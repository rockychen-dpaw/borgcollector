import django.forms
from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList
from django.forms.fields import Field, FileField


class BorgModelForm(django.forms.ModelForm):
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=None,
                 empty_permitted=False, instance=None):
        super(BorgModelForm,self).__init__(data,files,auto_id,prefix,initial,error_class,label_suffix,empty_permitted,instance)
        self._editing = True
        if data and any(key in data for key in ["_save","_continue","saveasnew","addanother"]):
            self._editing = False

    @property
    def editing(self):
        return self._editing

    def _clean_fields(self):
        for name, field in self.fields.items():
            # value_from_datadict() gets the data from the data dictionaries.
            # Each widget type knows how to retrieve its own data, because some
            # widgets split data over several HTML fields.
            value = field.widget.value_from_datadict(self.data, self.files, self.add_prefix(name))
            try:
                if self.editing and ( not value or not value.strip()):
                    #empty value, ignore check in editing mode
                    self.cleaned_data[name] = value.strip() if value else None
                    continue

                if isinstance(field, FileField):
                    initial = self.initial.get(name, field.initial)
                    value = field.clean(value, initial)
                else:
                    value = field.clean(value)
                self.cleaned_data[name] = value
                if hasattr(self, 'clean_%s' % name):
                    value = getattr(self, 'clean_%s' % name)()
                    self.cleaned_data[name] = value
            except ValidationError as e:
                self.add_error(name, e)

    def _post_clean(self):
        opts = self._meta
        # Update the model instance with self.cleaned_data.
        self.instance = django.forms.models.construct_instance(self, self.instance, opts.fields, opts.exclude)

        if self.editing:
            # in editing mode
            if hasattr(self.instance,"edit"):
                self.instance.edit()

            return

        exclude = self._get_validation_exclusions()

        # Foreign Keys being used to represent inline relationships
        # are excluded from basic field value validation. This is for two
        # reasons: firstly, the value may not be supplied (#12507; the
        # case of providing new values to the admin); secondly the
        # object being referred to may not yet fully exist (#12749).
        # However, these fields *must* be included in uniqueness checks,
        # so this can't be part of _get_validation_exclusions().
        for name, field in self.fields.items():
            if isinstance(field, django.forms.models.InlineForeignKeyField):
                exclude.append(name)

        try:
            self.instance.full_clean(exclude=exclude, validate_unique=False,form_cleaned=not bool(self._errors))
        except ValidationError as e:
            self._update_errors(e)

        # Validate uniqueness if needed.
        if self._validate_unique:
            self.validate_unique()

    
