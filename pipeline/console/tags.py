import argparse
import re
import sys
from typing import List

from tabulate import tabulate

from pipeline import PipelineCloud
from pipeline.schemas.pagination import Paginated
from pipeline.schemas.pipeline import (
    PipelineTagCreate,
    PipelineTagGet,
    PipelineTagPatch,
)
from pipeline.util.logging import _print

# We loosely follow the Docker tag conventions for valid tag names, specifically:
#
# - A tag name comprises a 'name' component and a 'tag' component in that order
#   separated by a colon, e.g. `name:tag`.
# - Name components may contain lowercase letters, digits and separators.
#   Separators are periods, underscores, dashes, and forward slashes.
#   A name component may not start or end with a separator.
# - A tag name must be valid ASCII and may contain lowercase and uppercase letters,
#   digits, underscores, periods and dashes. A tag name may not start with a period
#   or a dash and may contain a maximum of 128 characters.
VALID_TAG_NAME = re.compile(
    r"^[a-z0-9][a-z0-9-._/]*[a-z0-9]:[0-9A-Za-z_][0-9A-Za-z-_.]{0,127}$"
)


def _get_tag(tag_name: str) -> PipelineTagGet:
    if not VALID_TAG_NAME.match(tag_name):
        _print("Source tag must match pattern 'pipeline:tag'", level="ERROR")
        raise sys.exit(1)

    remote_service = PipelineCloud(verbose=False)
    tag_information = PipelineTagGet.parse_obj(
        remote_service._get(f"/v2/pipeline-tags/by-name/{tag_name}")
    )
    return tag_information


def _update_or_create_tag(source: str, target: str, sub_command: str) -> PipelineTagGet:
    remote_service = PipelineCloud(verbose=False)
    if not VALID_TAG_NAME.match(target):
        _print("Target tag must match pattern 'pipeline:tag'", level="ERROR")
        raise sys.exit(1)

    if VALID_TAG_NAME.match(source):
        # Pointing to another tag
        source_schema = _get_tag(source)
        source_pipeline = source_schema.pipeline_id
    else:
        # Pointing to a pipeline_id
        source_pipeline = source

    if sub_command == "create":
        tag_create_schema = PipelineTagCreate(
            name=target,
            pipeline_id=source_pipeline,
        )
        response = remote_service._post(
            "/v2/pipeline-tags", json_data=tag_create_schema.dict()
        )
    else:
        # Update
        existing_tag = _get_tag(target)
        patch_schema = PipelineTagPatch(pipeline_id=source_pipeline)
        response = remote_service._patch(
            f"/v2/pipeline-tags/{existing_tag.id}", json_data=patch_schema.dict()
        )

    tag_get_schema = PipelineTagGet.parse_obj(response)
    return tag_get_schema


def _list_tags(
    skip: int, limit: int, pipeline_id: str = None
) -> Paginated[PipelineTagGet]:
    remote_service = PipelineCloud(verbose=False)
    response = remote_service._get(
        "/v2/pipeline-tags",
        params=dict(
            skip=skip,
            limit=limit,
            order_by="created_at:desc",
            pipeline_id=pipeline_id,
        ),
    )

    paginated_results = Paginated[PipelineTagGet].parse_obj(response)

    return paginated_results


def _delete_tag(tag_name: str) -> None:
    remote_service = PipelineCloud(verbose=False)

    tag_information = _get_tag(tag_name)
    remote_service._delete(f"/v2/pipeline-tags/{tag_information.id}")


def _tabulate_tags(tags: List[PipelineTagGet]) -> str:
    return tabulate(
        [
            [
                tag.id,
                tag.name,
                tag.pipeline_id,
            ]
            for tag in tags
        ],
        headers=[
            "ID",
            "Name",
            "Target",
        ],
        tablefmt="outline",
    )


def tags(args: argparse.Namespace) -> int:
    sub_command = getattr(args, "sub-command", None)

    if sub_command in ["create", "update"]:
        source = getattr(args, "source")
        target = getattr(args, "target")
        tag_get_schema = _update_or_create_tag(source, target, sub_command)
        _print(f"Tag '{tag_get_schema.name}' -> '{tag_get_schema.pipeline_id}'")
        return 0
    elif sub_command in ["list", "ls"]:
        pipeline_id: str = getattr(args, "pipeline_id", None)
        paginated_results = _list_tags(
            getattr(args, "skip"),
            getattr(args, "limit"),
            pipeline_id=pipeline_id,
        )
        table_string = _tabulate_tags(paginated_results.data)
        print(table_string)
        return 0
    elif sub_command in ["delete", "rm"]:
        tag_name = getattr(args, "pipeline_tag")
        _delete_tag(tag_name)
        _print(f"Deleted {tag_name}")
        return 0
    elif sub_command == "get":
        tag_name = getattr(args, "pipeline_tag")
        tag_information = _get_tag(tag_name)
        table_string = _tabulate_tags([tag_information])
        print(table_string)
        return 0
