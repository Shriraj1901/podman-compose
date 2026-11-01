# SPDX-License-Identifier: GPL-2.0

import argparse
import contextlib
import io
import json
import unittest
from typing import Any
from unittest import mock

from podman_compose import compose_port


def get_compose(ports: dict[str, Any]) -> mock.Mock:
    compose = mock.Mock(unsafe=True)
    compose.container_names_by_service = {"web": ["project_web_1"]}
    compose.podman.output = mock.AsyncMock(
        return_value=json.dumps([{"NetworkSettings": {"Ports": ports}}]).encode("utf-8")
    )
    return compose


def get_args(**kwargs: Any) -> argparse.Namespace:
    args = argparse.Namespace(service="web", private_port=8080, protocol="tcp", index=1)
    for key, value in kwargs.items():
        setattr(args, key, value)
    return args


class TestComposePort(unittest.IsolatedAsyncioTestCase):
    async def run_port(self, compose: mock.Mock, args: argparse.Namespace) -> str:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            await compose_port(compose, args)
        return stdout.getvalue()

    async def test_prints_host_ip_and_port(self) -> None:
        compose = get_compose({"8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": "18080"}]})

        self.assertEqual(await self.run_port(compose, get_args()), "127.0.0.1:18080\n")

    async def test_empty_host_ip_means_all_interfaces(self) -> None:
        compose = get_compose({"8080/tcp": [{"HostIp": "", "HostPort": "18080"}]})

        self.assertEqual(await self.run_port(compose, get_args()), "0.0.0.0:18080\n")

    async def test_missing_host_ip_means_all_interfaces(self) -> None:
        compose = get_compose({"8080/tcp": [{"HostPort": "18080"}]})

        self.assertEqual(await self.run_port(compose, get_args()), "0.0.0.0:18080\n")

    async def test_ipv6_host_ip_is_bracketed(self) -> None:
        compose = get_compose({"8080/tcp": [{"HostIp": "::1", "HostPort": "18080"}]})

        self.assertEqual(await self.run_port(compose, get_args()), "[::1]:18080\n")

    async def test_udp_protocol(self) -> None:
        compose = get_compose({"8080/udp": [{"HostIp": "", "HostPort": "18081"}]})

        self.assertEqual(await self.run_port(compose, get_args(protocol="udp")), "0.0.0.0:18081\n")
