"""The module boundaries that bustan enforces when it builds the application.

These tests use small modules of their own, not the modules of the sample.
They prove the claims of docs/explanation/bustan-or-fastapi.md.
"""

import asyncio

import pytest
from bustan import ExportViolationError, Injectable, Module, ProviderResolutionError
from bustan.testing import create_testing_module


@Injectable()
class Ledger:
    pass


@Injectable()
class Payments:
    def __init__(self, ledger: Ledger) -> None:
        self.ledger = ledger


# Ledger is private to the module. Only Payments is exported.
@Module(providers=[Ledger, Payments], exports=[Payments])
class PaymentsModule:
    pass


@Injectable()
class Reports:
    def __init__(self, ledger: Ledger) -> None:
        self.ledger = ledger


@Module(imports=[PaymentsModule], providers=[Reports])
class ReportsModule:
    pass


@Injectable()
class Invoices:
    def __init__(self, payments: Payments) -> None:
        self.payments = payments


@Module(providers=[Invoices])
class InvoicesModule:
    pass


@Module(imports=[PaymentsModule], providers=[Invoices])
class BillingModule:
    pass


@Module(exports=[Ledger])
class ExportsWhatItDoesNotOwn:
    pass


def _compile(root: type) -> None:
    async def scenario() -> None:
        compiled = await create_testing_module(root).compile()
        await compiled.close()

    asyncio.run(scenario())


def test_a_module_cannot_use_a_provider_that_is_not_exported() -> None:
    with pytest.raises(
        ProviderResolutionError, match=r"needs .*Ledger, which ReportsModule cannot see"
    ):
        _compile(ReportsModule)


def test_a_module_cannot_use_a_provider_of_a_module_that_it_does_not_import() -> None:
    with pytest.raises(ProviderResolutionError, match="import a module that exports it"):
        _compile(InvoicesModule)


def test_a_module_that_imports_the_exporting_module_can_use_the_export() -> None:
    _compile(BillingModule)


def test_a_module_cannot_export_a_provider_that_it_does_not_own() -> None:
    with pytest.raises(ExportViolationError, match="neither provided nor imported"):
        _compile(ExportsWhatItDoesNotOwn)
