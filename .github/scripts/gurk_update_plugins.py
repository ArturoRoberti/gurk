try:
    from gurk.lib.context import GurkContext, Logger, get_registries
    from gurk.lib.core.plugins import upgrade_plugin
except ImportError:
    raise ImportError(
        "The gurk package needs to be installed to run this script."
    )

if __name__ == "__main__":
    with GurkContext(
        logger=Logger(verbose=True, non_interactive=True, store_logs=False),
        writable=True,
    ):
        if not all(
            upgrade_plugin(name, require_local=False)
            for name in get_registries(
                home_registry=False, package_registry=True
            ).keys()
        ):
            raise SystemExit(1)
