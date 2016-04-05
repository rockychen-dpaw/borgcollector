from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_save,post_save,post_delete
from django.dispatch import receiver

from borg_utils.resource_status import ResourceStatus
from tablemanager.models import Publish

class PublishAction(object):
    """
    Represent all the pending actions after last publish
    """
    publish_all_action = 1
    publish_data_action = 4
    publish_feature_action = 256 
    publish_gwc_action = 512

    _change_type_mapping = {
        "sql": publish_data_action,
        "input_table":publish_data_action,
        "relation_1":publish_data_action,
        "relation_2":publish_data_action,
        "relation_3":publish_data_action,
        "normal_tables":publish_data_action,
        "create_extra_index_sql": publish_data_action,
        "geoserver_setting":publish_gwc_action
    }

    _forbidding_columns = ["name","workspace"]
    def __init__(self,action=0):
        self._action = action or 0
        self._possible_data_changed = False

    def __bool__(self):
        return self._action == 0

    def __nonzero__(self):
        return self.__bool__()

    def __str__(self):
        result = ""
        if self.publish_all:
            result = "All"
        else:
            if self.publish_data:
                result = "Data"
            elif self._possible_data_changed:
                result = "Data?"
            if self.publish_feature or self.publish_gwc:
                result += "Metadata" if result == "" else " , Metadata"
        return result

    @property
    def possible_data_changed(self):
        return self._possible_data_changed

    @possible_data_changed.setter
    def possible_data_changed(self,value):
        self._possible_data_changed = value

    def edit(self,instance):
        existing_instance = None
        if instance.pk:
            existing_instance = Publish.objects.get(pk = instance.pk)

        self._action = instance.pending_actions or 0
        if existing_instance:
            for f in  instance._meta.fields:
                if f.name not in self._change_type_mapping:
                    continue
                rel1 = getattr(instance,f.name)
                rel2 = getattr(existing_instance,f.name)
                if f.name in ["relation_1","relation_2","relation_3"]:
                    if (rel1 == None or rel1.is_empty):
                        if (rel2 == None or rel2.is_empty):
                            pass
                        else:
                            self.column_changed(f.name)
                    elif (rel2 == None or rel2.is_empty):
                        self.column_changed(f.name)
                    else:
                        index = 0
                        for t in rel1.normal_tables:
                            if t == rel2.normal_tables[index]:
                                pass
                            else:
                                self.column_changed(f.name)
                                break;
                            index += 1
                elif f.name == "status":
                    if rel1 != ResourceStatus.Enabled.name:
                        self._action = 0
                        break
                    elif rel1 != rel2:
                        self._action = self.publish_all_action
                        break
                else:
                    if rel1 != rel2:
                        self.column_changed(f.name)
        else:
            self._action = self.publish_all_action

        return self

    def column_changed(self,column):
        if self._action == self.publish_all_action:
            return self

        if column in self._forbidding_columns:
            raise ValidationError("Changing the column ({0}) value is not supportted".format(column))
        self._action |= self._change_type_mapping.get(column,0)
        return self
        

    def _clear_action(self,action):
        self._action &= ~action

    @property
    def actions(self):
        return self._action or None

    @property
    def has_action(self):
        return self._action > 0

    def clear_all_action(self):
        self._action = 0

    @property
    def publish_all(self):
        return self._action & self.publish_all_action == self.publish_all_action

    def clear_all_action(self):
        self._action = 0
        return self

    @property
    def publish_gwc(self):
        return self._action & self.publish_gwc_action == self.publish_gwc_action

    def clear_gwc_action(self):
        self._clear_action(self.publish_gwc_action)
        return self

    @property
    def publish_data(self):
        return self._action & self.publish_data_action == self.publish_data_action

    def clear_data_action(self):
        self._clear_action(self.publish_data_action)
        return self

    @property
    def publish_feature(self):
        return self._action & self.publish_feature_action == self.publish_feature_action

    def clear_feature_action(self):
        self._clear_action(self.publish_feature_action)
        return self

class PublishActionEventListener(object):
    @staticmethod
    @receiver(pre_save, sender=Publish)
    def _publish_pre_save(sender, instance, **args):
        if "update_fields" in args and args["update_fields"]:
            if len(args["update_fields"]) == 1 and "pending_actions" in args["update_fields"]:
                return
            elif "status" in args["update_fields"] and instance.status == ResourceStatus.Enabled.name:
                instance.pending_actions = PublishAction.publish_all_action
                return

        instance.pending_actions = PublishAction().edit(instance).actions


