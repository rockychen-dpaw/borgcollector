import os
from datetime import datetime
import pytz

from django.utils import timezone
from django.conf import settings

from tablemanager.models import Publish
from harvest.models import Job
from borg_utils.resource_status import ResourceStatus,ResourceStatusManagement

def migrate():
    """
    Migrate meta data to csw
    """
    if not hasattr(Publish(),"kmi_title"):
        #kmi title not found, migrate finished
        raise Exception("Migrate to csw has finished.")
    from tablemanager.models import Style

    for p in Publish.objects.all():
        if p.status != ResourceStatus.Enabled.name:
            #not enabled
            continue
        if not p.job_id: 
            #not published
            continue
        job = None
        try:
            job = Job.objects.get(pk=p.job_id)
        except:
            #job not exist
            pass

        

        modify_time = None
        meta_data = p.builtin_metadata
        meta_data["auto_update"] = True
        if p.kmi_title and p.kmi_title.strip():
            #has customized title
            meta_data["title"] = p.kmi_title
            meta_data["auto_update"] = False

        if p.kmi_abstract and p.kmi_abstract.strip():
            #has customized abstract
            meta_data["abstract"] = p.kmi_abstract
            meta_data["auto_update"] = False

        #get builtin style
        builtin_style = None
        for style in meta_data.get("styles",[]):
            if style["format"].lower() == "sld":
                builtin_style = style
                break

        #set auto update flag
        for style in meta_data.get("styles",[]):
            style["auto_update"] = True

        #remove sld style file
        meta_data["styles"] = [style for style in meta_data.get("styles",[]) if style["format"].lower() != "sld"]

        #populate sld style files
        styles = {}
        if builtin_style and p.default_style and p.default_style.name == "builtin":
            #builtin style is the default style
            builtin_style["default"] = True
            meta_data["styles"].append(builtin_style)

        for style in p.style_set.exclude(name="builtin").filter(status="Enabled"):
            style_data = {"format":"SLD"}
            style_data["auto_update"] = False
            if style.name == "customized":
                if builtin_style:
                    #has builtin style, this customized is the revised version of buitlin style
                    pass
                else:
                    #no builtin style,change the name "customized"  to "initial"
                    style_data["name"] = "initial"
            else:
                style_data["name"] = style.name

            if style == p.default_style:
                style_data["default"] = True

            if not style.sld or not style.sld.strip():
                #sld is empty
                continue
            style_data["raw_content"] = style.sld.encode("base64")
            meta_data["styles"].append(style)
                
        if meta_data["auto_update"]:
            if p.input_table:
                for ds in p.input_table.datasource:
                    if os.path.exists(ds):
                        input_modify_time = datetime.utcfromtimestamp(os.path.getmtime(ds)).replace(tzinfo=pytz.UTC)
                        if modify_time:
                            if modify_time < input_modify_time:
                                modify_time = input_modify_time
                        else:
                            modify_time = input_modify_time
        else:
            modify_time = p.last_modify_time

        if job:
            #job exist
            publish_time = job.finished
        else:
            #job not exist
            publish_time = timezone.now()

        insert_time = modify_time if modify_time <= publish_time else publish_time

        meta_data["insert_date"] = insert_time
        meta_data["modified"] = modify_time
        meta_data["publication_date"] = publish_time

        #update catalogue service
        res = request.post("{}/catalogue/api/records/".format(settings.CSW_URL),data=meta_data,auth=(settings.CSW_USER,settings.CSW_PASSWORD))
        res.raise_for_status()




        



