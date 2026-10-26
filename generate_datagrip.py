#!/usr/bin/env python3
"""Generate local DataGrip connections with plaintext credentials from Compose."""

import json
from pathlib import Path
import subprocess
import uuid
from urllib.parse import urlencode
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
COMPOSE = ROOT / "database" / "docker-compose.yml"
OUTPUT = ROOT / ".idea" / "dataSources.xml"


def main() -> None:
    result = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), "config", "--format", "json"],
        check=True, capture_output=True, text=True,
    )
    services = json.loads(result.stdout)["services"]
    if OUTPUT.exists():
        tree = ET.parse(OUTPUT)
        project = tree.getroot()
    else:
        project = ET.Element("project", version="4")
        tree = ET.ElementTree(project)
    component = project.find("./component[@name='DataSourceManagerImpl']")
    if component is None:
        component = ET.SubElement(project, "component", {
            "name": "DataSourceManagerImpl", "format": "xml", "multifile-model": "true"
        })

    drivers = {
        "oracle": ("oracle", "oracle.jdbc.OracleDriver", 1521),
        "oracle-system": ("oracle", "oracle.jdbc.OracleDriver", 1521),
        "postgres": ("postgresql", "org.postgresql.Driver", 5432),
        "mysql": ("mysql.8", "com.mysql.cj.jdbc.Driver", 3306),
        "mssql": ("sqlserver.jb", "com.microsoft.sqlserver.jdbc.SQLServerDriver", 1433),
    }
    for service, (driver, driver_class, target_port) in drivers.items():
        config = services.get("oracle" if service == "oracle-system" else service)
        if config is None:
            continue
        port = next(p for p in config["ports"] if int(p["target"]) == target_port)
        host = port.get("host_ip") or "127.0.0.1"
        if host in ("0.0.0.0", "::"):
            host = "127.0.0.1"
        if ":" in host:
            host = f"[{host}]"
        address = f"{host}:{port['published']}"
        env = config.get("environment", {})
        if service in ("oracle", "oracle-system"):
            admin = service == "oracle-system"
            user = "SYSTEM" if admin else env.get("APP_USER", "developer")
            password_key = "ORACLE_PASSWORD" if admin else "APP_USER_PASSWORD"
            password = env.get(password_key)
            if not password:
                raise SystemExit(f"Oracle {password_key} is empty; configure DB_PASSWORD first.")
            if '"' in user or '"' in password:
                raise SystemExit('Oracle URL credentials cannot contain double quotes.')
            url = f'jdbc:oracle:thin:"{user}"/"{password}"@//{address}/FREEPDB1'
        elif service == "postgres":
            user = env.get("POSTGRES_USER", "postgres")
            password = env.get("POSTGRES_PASSWORD")
            url = f"jdbc:postgresql://{address}/{env.get('POSTGRES_DB', user)}"
        elif service == "mysql":
            user = env.get("MYSQL_USER", "root")
            password = env.get("MYSQL_PASSWORD" if user != "root" else "MYSQL_ROOT_PASSWORD")
            url = f"jdbc:mysql://{address}/{env.get('MYSQL_DATABASE', '')}"
        else:
            user = "sa"
            password = env.get("MSSQL_SA_PASSWORD")
            url = (f"jdbc:sqlserver://{address};databaseName=master;"
                   "encrypt=true;trustServerCertificate=true")

        if not password:
            raise SystemExit(f"Password for {service} is empty; configure DB_PASSWORD first.")
        if service in ("postgres", "mysql"):
            url += "?" + urlencode({"user": user, "password": password})
        elif service == "mssql":
            url += ";user={sa};password={" + password.replace("}", "}}") + "}"

        identifier = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{ROOT.as_uri()}/datagrip/{service}"))
        source = component.find(f"./data-source[@uuid='{identifier}']")
        if source is None:
            source = ET.SubElement(component, "data-source", {
                "source": "LOCAL", "name": f"metadata-miner / {service}", "uuid": identifier,
            })
        for tag, value in (
            ("driver-ref", driver), ("jdbc-driver", driver_class),
            ("jdbc-url", url), ("user-name", user),
            ("auth-provider", "no-auth"), ("synchronize", "true"),
        ):
            element = source.find(tag)
            if element is None:
                element = ET.SubElement(source, tag)
            element.text = value
        # URL-only mode keeps DataGrip from rebuilding the credential-bearing URL.
        configuration = source.find("configuration")
        if configuration is None:
            configuration = ET.SubElement(source, "configuration")
        option = configuration.find("./option[@name='CONFIG_TYPE']")
        if option is None:
            option = ET.SubElement(configuration, "option", name="CONFIG_TYPE")
        option.set("value", "URL_ONLY")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(tree, space="  ")
    temporary = OUTPUT.with_suffix(".xml.tmp")
    temporary.touch(mode=0o600, exist_ok=True)
    temporary.chmod(0o600)
    tree.write(temporary, encoding="UTF-8", xml_declaration=True)
    temporary.replace(OUTPUT)
    print(f"Generated {OUTPUT}")
    print("Credentials are stored in plaintext in this local file. Reload the project in DataGrip.")


if __name__ == "__main__":
    main()
