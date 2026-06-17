"""Pluggable data connectors. Each maps a provider's series into schema names."""
from data.connectors.base import Connector
from data.connectors.dbnomics import DBnomicsConnector
from data.connectors.epoch import EpochConnector
from data.connectors.oecd_idd import OECDIDDConnector

__all__ = ["Connector", "DBnomicsConnector", "EpochConnector", "OECDIDDConnector"]
