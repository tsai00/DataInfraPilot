import pathlib

import yaml
from pyhelm3 import Client, Chart, ReleaseRevision, mergeconcat
from typing import Annotated, Any
from pydantic import Field, DirectoryPath, FilePath, HttpUrl
from yaml import SafeLoader

Name = Annotated[str, Field(pattern=r"^[a-z0-9-]+$")]
OCIPath = Annotated[str, Field(pattern=r"oci:\/\/*")]


class HelmChartOCI(Chart):
    ref: DirectoryPath | FilePath | HttpUrl | OCIPath | Name = Field(
        ...,
    )
    repo: HttpUrl | OCIPath | None = Field(None, description="The repository URL.")


class HelmClient(Client):
    async def get_oci_chart(self, chart_ref, *, devel=False, repo=None, version=None):
        metadata = await self._show_oci_chart(
            chart_ref,
            devel=devel,
            repo=repo,
            version=version
        )
        return HelmChartOCI(
            _command=self._command,
            ref=chart_ref,
            repo=repo,
            metadata=metadata
        )

    async def install_or_upgrade_oci_release(
            self,
            release_name: str,
            chart: Chart,
            *values: dict[str, Any],
            atomic: bool = False,
            cleanup_on_fail: bool = False,
            create_namespace: bool = True,
            description: str | None = None,
            dry_run: bool = False,
            force: bool = False,
            namespace: str | None = None,
            no_hooks: bool = False,
            reset_values: bool = False,
            reuse_values: bool = False,
            skip_crds: bool = False,
            timeout: int | str | None = None,
            wait: bool = False
    ) -> ReleaseRevision:
        """
        Install or upgrade the named release using the given chart and values and return
        the new revision.
        """
        return ReleaseRevision._from_status(
            await self._command.install_or_upgrade(
                release_name,
                f'{chart.repo}/{chart.ref}',
                mergeconcat(*values) if values else None,
                atomic=atomic,
                cleanup_on_fail=cleanup_on_fail,
                create_namespace=create_namespace,
                description=description,
                dry_run=dry_run,
                force=force,
                namespace=namespace,
                no_hooks=no_hooks,
                reset_values=reset_values,
                reuse_values=reuse_values,
                skip_crds=skip_crds,
                timeout=timeout,
                version=chart.metadata.version,
                wait=wait
            ),
            self._command
        )

    async def _show_oci_chart(
        self,
        chart_ref: pathlib.Path | str,
        *,
        devel: bool = False,
        repo: str | None = None,
        version: str | None = None
    ) -> dict[str, Any]:
        """
        Returns the contents of Chart.yaml for the specified chart.
        """
        command = ["show", "chart", f'{repo}/{chart_ref}']
        if devel:
            command.append("--devel")
        if self._command._insecure_skip_tls_verify:
            command.append("--insecure-skip-tls-verify")
        if version:
            command.extend(["--version", version])
        return yaml.load(await self._command.run(command), Loader=SafeLoader)

