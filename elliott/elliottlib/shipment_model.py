from __future__ import annotations
from datetime import datetime, timezone

from typing import Union, List, Optional, Self, Literal

from ruamel.yaml import scalarstring
from pydantic import BaseModel, Field, field_serializer, ConfigDict, model_validator


class Metadata(BaseModel):
    """ Defines shipment metadata for a product release """

    product: str  # product associated with shipment - see group.yml `product` field
    application: str  # Konflux application to release for
    group: str  # associated build-data group for component metadata
    assembly: str  # associated build-data assembly
    fbc: Optional[bool] = False  # indicates if shipment is for an FBC release


class Spec(BaseModel):
    """ Defines spec of a Konflux Snapshot - list of NVRs that should go inside the snapshot """

    nvrs: List


class Snapshot(BaseModel):
    """ Konflux Snapshot definition for release i.e. builds to release """

    name: str  # Name of the snapshot to release - required until we create automatically by spec
    spec: Spec


class CveAssociation(BaseModel):
    key: str
    component: str


class Issue(BaseModel):
    id: Union[str, int]
    source: str


class Issues(BaseModel):
    fixed: Optional[List[Issue]] = None


class ReleaseNotes(BaseModel):
    """ Represents releaseNotes field which contains all advisory metadata, when constructing a Konflux release """

    type: Literal['RHEA', 'RHBA', 'RHSA']  # Advisory type
    synopsis: str
    topic: str
    description: str
    solution: str

    # Konflux pipeline expects certain keys like issues, cves to always be set, even if empty
    # therefore allow these to have default empty values
    issues: Optional[Issues] = {}
    cves: Optional[List[CveAssociation]] = []

    references: Optional[List[str]] = None

    # serialize special text fields, if they contain a new-line char
    # configure them to be LiteralScalarString
    @field_serializer('topic', 'solution', 'description')
    def serialize_text_fields(self, field: str, _info):
        if '\n' in field:
            return scalarstring.LiteralScalarString(field)
        return field


class Data(BaseModel):
    """ Represents spec.data field when constructing a Konflux release """

    releaseNotes: ReleaseNotes


class ShipmentEnv(BaseModel):
    """ Environment specific configuration for a release """

    releasePlan: str
    releaseName: Optional[str] = None
    advisoryName: Optional[str] = None
    advisoryInternalUrl: Optional[str] = None

    def shipped(self):
        if self.releaseName or self.advisoryName or self.advisoryInternalUrl:
            return True


class Environments(BaseModel):
    """ Environments to release the shipment to """

    stage: ShipmentEnv = Field(
        ..., description='Config for releasing to stage environment'
    )
    prod: ShipmentEnv = Field(
        ..., description='Config for releasing to prod environment'
    )


class Shipment(BaseModel):
    """ Config to ship a Konflux release for a product """

    metadata: Metadata
    environments: Environments
    snapshot: Snapshot
    data: Optional[Data] = None

    @model_validator(mode='after')
    def make_sure_data_is_present_unless_fbc(self) -> Self:
        release_notes_present = self.data and self.data.releaseNotes
        if self.metadata.fbc and release_notes_present:
            raise ValueError('FBC shipment is not expected to have data.releaseNotes defined')
        if not self.metadata.fbc and not release_notes_present:
            raise ValueError('A regular shipment is expected to have data.releaseNotes defined')
        return self


def add_schema_comment(schema: dict):
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M %Z")
    comment = f'Schema generated on {timestamp} from {__name__}'
    schema['$comment'] = comment


class ShipmentConfig(BaseModel):
    """ Represents a Shipment Metadata Config file in a product's shipment-data repo """

    model_config = ConfigDict(json_schema_extra=add_schema_comment)

    shipment: Shipment
