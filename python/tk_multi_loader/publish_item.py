import os
import sgtk
from tank.util import sgre as re

logger = sgtk.platform.get_logger(__name__)


class PublishItem():
    """
   Publish Item
    """

    def __init__(self, sg_item):
        self.sg_item = sg_item
        self.entity = None
        self.settings = {
            "wire": "Alias File",
            "abc": "Alembic Cache",
            "max": "3dsmax Scene",
            "hrox": "NukeStudio Project",
            "hip": "Houdini Scene",
            "hipnc": "Houdini Scene",
            "ma": "Maya Scene",
            "mb": "Maya Scene",
            "fbx": "Motion Builder FBX",
            "nk": "Nuke Script",
            "psd": "Photoshop Image",
            "psb": "Photoshop Image",
            "vpb": "VRED Scene",
            "vpe": "VRED Scene",
            "osb": "VRED Scene",
            "dpx": "Rendered Image",
            "exr": "Rendered Image",
            "tiff": "Texture",
            "tx": "Texture",
            "tga": "Texture",
            "dds": "Texture",
            "jpeg": "Image",
            "jpg":  "Image",
            "mov": "Movie",
            "mp4": "Movie",
            "pdf": "PDF"
        }

    def publish_file(self):
        """
        Publish the file
        """

        publish_path = self.get_publish_path()
        if not publish_path:
            logger.info("Unable to find publish file")
            return

        publish_name = self.get_publish_name(publish_path)


        entity = self.get_publish_entity()
        entity_type = entity.get("type", None)
        entity_id = entity.get("id", 0)

        # tk = sgtk.sgtk_from_path(publish_path)
        tk = sgtk.sgtk_from_entity(entity_type, entity_id)

        # ctx = tk.context_from_path(publish_path)
        ctx = tk.context_from_entity(entity_type, entity_id)

        logger.debug(">>>>>>>>>>>> entity is: {}".format(entity))
        logger.debug(">>>>>>>>>>>> tk is: {}".format(tk))
        logger.debug(">>>>>>>>>>>> context is: {}".format(ctx))


        publish_type = self.get_publish_type(publish_path)

        publish_version = self.get_publish_version()
        publish_fields = self.get_publish_fields()
        description = self.get_description()

        #publish_dependencies_paths = self.get_publish_dependencies(settings, item)
        # publish_user = self.get_publish_user(settings, item)

        logger.info("Registering publish...")
        publish_data = {
            "tk": tk,
            "context": ctx,
            "entity": entity,
            "comment": description,
            "path": publish_path,
            "name": publish_name,
            "version_number": publish_version,
            "published_file_type": publish_type,
            "sg_fields": publish_fields,
            # "created_by": publish_user,
            # "thumbnail_path": item.get_thumbnail_as_path(),
            #"dependency_paths": publish_dependencies_paths,
            #"dependency_ids": publish_dependencies_ids,

        }

        # logger.debug("publish data: {}".format(publish_data))

        # create the publish and stash it in the item properties for other
        # plugins to use.
        sg_publish_result = sgtk.util.register_publish(**publish_data)

        logger.info("Publish registered!")
        # logger.debug(">>>>> Publish result: {}".format(sg_publish_result))
        if sg_publish_result:
            logger.debug(">>>>>>>>>>>> Publish result begin: ")
            for k, v in sg_publish_result.items():
                logger.debug("{}: {}".format(k, v))
            logger.debug(">>>>>>>>>>>> End of Publish result: ")

        return sg_publish_result


    def get_publish_entity(self):
        publish_entity = {}
        entity = self.sg_item.get("entity", None)
        if entity:
            publish_entity["id"] = entity.get("id", None)
            publish_entity["name"] = entity.get("code", None)
            publish_entity["type"] = entity.get("type", None)
        return publish_entity

    def get_publish_path(self):
        """
        Get publish path
        """
        # file_to_publish
        file_to_publish = None
        if 'path' in self.sg_item:
            file_to_publish = self.sg_item['path'].get('local_path', None)
        return file_to_publish

    def get_publish_name(self, file_to_publish):
        """
        Get publish name
        """
        return os.path.basename(file_to_publish)

    def get_publish_type(self, publish_path):
        """
        Get a publish type
        """
        publish_type = None
        publish_path = os.path.splitext(publish_path)
        if len(publish_path) >= 2:
            extension = publish_path[1]

            # ensure lowercase and no dot
            if extension:
                extension = extension.lstrip(".").lower()
                publish_type = self.settings.get(extension, None)
                if not publish_type:
                    # publish type is based on extension
                    publish_type = "%s File" % extension.capitalize()
            else:
                # no extension, assume it is a folder
                publish_type = "Folder"
        return publish_type


    def get_publish_user(self, settings, item):
        """
        Get the user that will be associated with this publish.

        If publish_user is not defined as a ``property`` or ``local_property``,
        this method will return ``None``.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish template for

        :return: A user entity dictionary or ``None`` if not defined.
        """
        pass

    def get_publish_version(self):

        # use the p4 revision number as the version number
        return int(self.sg_item.get("headRev", 0))

    def get_publish_fields(self):
        sg_fields = {}
        sg_fields["sg_p4_depo_path"] = self.sg_item.get("depotFile", None)
        sg_fields["sg_p4_change_number"] = int(self.sg_item.get("headChange", None))
        # sg_fields["Status"] = self.sg_item.get("headAction", None)
        sg_fields["sg_status_list"] = self.sg_item.get("sg_status_list", None)
        # sg_fields["link"] = self.entity.get("name", None)
        # logger.debug(">>>>> Publish sg_fields: {}".format(sg_fields))

        return sg_fields

    def get_description(self):
        return self.sg_item.get("description", None)

    def get_next_version_number(self, item, path):

        # See how many prior versions there are
        filters = [
            ['entity', 'is', self._get_version_entity(item)]
        ]
        prior_versions = self.publisher.shotgun.find("Version",filters,['code'])

        #regex = r"(" + re.escape(publish_name.split('.')[0]) + r"){1}(\.v\d)?\.\w*$"
        regex = r"(" + re.escape(publish_name) + r"){1}(\.v\d)?\.\w*$"

        x = [i for i in prior_versions if re.match(regex,i['code'])]

        # Set the publish name of this item as the next version
        version_number = len(x)+1

        return version_number

    def _get_version_entity(self, item):
        """
        Returns the best entity to link the version to.
        """

        if item.context.entity:
            return item.context.entity
        elif item.context.project:
            return item.context.project
        else:
            return None



