from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .retrieval import EQUIPMENT_LABELS, RetrievalHit
from .settings import settings


@dataclass
class GraphRecordSet:
    nodes: dict[str, dict[str, str]]
    edges: set[tuple[str, str, str]]


def _node_id(prefix: str, *parts: object) -> str:
    raw = ":".join(str(part or "").strip() for part in parts)
    cleaned = raw.replace(" ", "_").replace("/", "_").replace("\\", "_")
    return f"{prefix}:{cleaned}"[:220]


def _add_node(nodes: dict[str, dict[str, str]], node_id: str, label: str, node_type: str) -> None:
    if not label:
        label = node_id
    nodes[node_id] = {"id": node_id, "label": str(label), "type": node_type}


def _add_edge(edges: set[tuple[str, str, str]], source: str, target: str, relation: str) -> None:
    if source and target and source != target:
        edges.add((source, target, relation))


def _equipment_label(equipment: str) -> str:
    return EQUIPMENT_LABELS.get(equipment, equipment or "设备")


def collect_graph_records(conn: sqlite3.Connection) -> GraphRecordSet:
    nodes: dict[str, dict[str, str]] = {}
    edges: set[tuple[str, str, str]] = set()

    manual_rows = conn.execute(
        """
        SELECT id, title, equipment, component, fault_type, section, source, page
        FROM manual_chunks
        """
    ).fetchall()
    for row in manual_rows:
        equipment = row["equipment"] or "general"
        component = row["component"] or "设备"
        fault = row["fault_type"] or "通用检修"
        equipment_id = _node_id("equipment", equipment)
        component_id = _node_id("component", equipment, component)
        fault_id = _node_id("fault", equipment, fault)
        chunk_id = _node_id("chunk", row["id"])
        safety_id = _node_id("safety", equipment, fault)
        _add_node(nodes, equipment_id, _equipment_label(equipment), "Equipment")
        _add_node(nodes, component_id, component, "Component")
        _add_node(nodes, fault_id, fault, "Fault")
        _add_node(nodes, chunk_id, f"{row['title']} P{row['page']}", "ManualChunk")
        _add_node(nodes, safety_id, f"{fault}安全规则", "SafetyRule")
        _add_edge(edges, equipment_id, component_id, "HAS_COMPONENT")
        _add_edge(edges, component_id, fault_id, "HAS_FAULT")
        _add_edge(edges, fault_id, safety_id, "HAS_SAFETY_RULE")
        _add_edge(edges, chunk_id, fault_id, "CITED_BY")

    case_rows = conn.execute(
        """
        SELECT id, title, equipment, fault_type, cause, actions, parts, status
        FROM maintenance_cases
        """
    ).fetchall()
    for row in case_rows:
        equipment = row["equipment"] or "general"
        fault = row["fault_type"] or "通用检修"
        case_id = _node_id("case", row["id"])
        fault_id = _node_id("fault", equipment, fault)
        cause_id = _node_id("cause", equipment, row["cause"][:40])
        step_id = _node_id("step", "case", row["id"])
        _add_node(nodes, case_id, row["title"], "Case")
        _add_node(nodes, fault_id, fault, "Fault")
        _add_node(nodes, cause_id, row["cause"][:80], "Cause")
        _add_node(nodes, step_id, row["actions"][:80], "Process")
        _add_edge(edges, case_id, fault_id, "OBSERVED_IN")
        _add_edge(edges, fault_id, cause_id, "HAS_CAUSE")
        _add_edge(edges, fault_id, step_id, "HAS_STEP")

    visual_rows = conn.execute(
        """
        SELECT id, filename, equipment, component, defect_labels, ocr_text
        FROM visual_assets
        """
    ).fetchall()
    for row in visual_rows:
        equipment = row["equipment"] or "general"
        visual_id = _node_id("visual", row["id"])
        equipment_id = _node_id("equipment", equipment)
        component_id = _node_id("component", equipment, row["component"] or "待确认部件")
        _add_node(nodes, visual_id, row["filename"], "VisualAsset")
        _add_node(nodes, equipment_id, _equipment_label(equipment), "Equipment")
        _add_node(nodes, component_id, row["component"] or "待确认部件", "Component")
        _add_edge(edges, visual_id, equipment_id, "OBSERVED_IN")
        _add_edge(edges, visual_id, component_id, "HAS_COMPONENT")
        for label in _defect_labels(row["defect_labels"]):
            fault_id = _node_id("fault", equipment, label)
            _add_node(nodes, fault_id, label, "Fault")
            _add_edge(edges, component_id, fault_id, "HAS_FAULT")
            _add_edge(edges, visual_id, fault_id, "OBSERVED_IN")

    return GraphRecordSet(nodes=nodes, edges=edges)


def _defect_labels(raw: str) -> list[str]:
    import json

    try:
        payload = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    labels = []
    for item in payload:
        if isinstance(item, dict) and item.get("label"):
            labels.append(str(item["label"]))
        elif isinstance(item, str):
            labels.append(item)
    return labels[:6]


def _safety_neighbors(fault: str) -> list[str]:
    if "泄漏" in fault:
        return ["隔离介质", "释放压力", "防滑警示", "试压验收"]
    if "火花塞" in fault or "压缩" in fault:
        return ["冷机拆装", "断开点火/喷油", "清洁火花塞孔", "防止误启动"]
    if "轴承" in fault or "剥落" in fault or "磨损" in fault:
        return ["PPE 防护", "清洁装配区", "禁止硬敲滚道", "空载试运行"]
    if "过热" in fault or "绝缘" in fault:
        return ["停机断电", "验电挂牌", "绝缘复测", "空载试运行"]
    return ["停机断电", "PPE 防护", "人工复核", "验收归档"]


def _hit_path(equipment: str, hit: RetrievalHit) -> dict[str, Any]:
    equipment_id = _node_id("equipment", equipment or hit.equipment)
    component_id = _node_id("component", equipment or hit.equipment, hit.component)
    fault_id = _node_id("fault", equipment or hit.equipment, hit.fault_type)
    step_id = _node_id("step", hit.source_type, hit.id)
    safety_id = _node_id("safety", equipment or hit.equipment, hit.fault_type)
    nodes = [
        {"id": equipment_id, "label": _equipment_label(equipment or hit.equipment), "type": "Equipment"},
        {"id": component_id, "label": hit.component or "部件", "type": "Component"},
        {"id": fault_id, "label": hit.fault_type or "待确认故障", "type": "Fault"},
        {"id": step_id, "label": "标准化 SOP", "type": "Process"},
        {"id": safety_id, "label": "合规校验", "type": "SafetyRule"},
    ]
    edges = [
        {"source": equipment_id, "target": component_id, "relation": "HAS_COMPONENT"},
        {"source": component_id, "target": fault_id, "relation": "HAS_FAULT"},
        {"source": fault_id, "target": step_id, "relation": "HAS_STEP"},
        {"source": step_id, "target": safety_id, "relation": "HAS_SAFETY_RULE"},
    ]
    return {
        "equipment": nodes[0]["label"],
        "component": nodes[1]["label"],
        "fault": nodes[2]["label"],
        "source_title": hit.title,
        "source_type": hit.source_type,
        "confidence": hit.confidence,
        "path": [node["label"] for node in nodes],
        "relations": [edge["relation"] for edge in edges],
        "nodes": nodes,
        "edges": edges,
        "safety_neighbors": _safety_neighbors(hit.fault_type or ""),
    }


class SQLiteGraphStore:
    def __init__(self, conn: sqlite3.Connection, *, backend: str = "sqlite", reason: str = "") -> None:
        self.conn = conn
        self.backend = backend
        self.reason = reason

    def status(self) -> dict[str, Any]:
        node_count = self.conn.execute("SELECT COUNT(*) AS c FROM kg_nodes").fetchone()["c"]
        edge_count = self.conn.execute("SELECT COUNT(*) AS c FROM kg_edges").fetchone()["c"]
        return {
            "backend": self.backend,
            "connected": True,
            "reason": self.reason,
            "node_count": node_count,
            "edge_count": edge_count,
            "last_sync": "",
        }

    def rebuild(self) -> dict[str, Any]:
        records = collect_graph_records(self.conn)
        self.conn.execute("DELETE FROM kg_edges")
        self.conn.execute("DELETE FROM kg_nodes")
        self.conn.executemany(
            "INSERT OR REPLACE INTO kg_nodes (id, label, type) VALUES (?, ?, ?)",
            [(node["id"], node["label"], node["type"]) for node in records.nodes.values()],
        )
        self.conn.executemany(
            "INSERT INTO kg_edges (source, target, relation) VALUES (?, ?, ?)",
            sorted(records.edges),
        )
        self.conn.commit()
        return {
            "backend": self.backend,
            "connected": True,
            "node_count": len(records.nodes),
            "edge_count": len(records.edges),
            "last_sync": datetime.utcnow().isoformat(timespec="seconds"),
        }

    def query_paths(
        self,
        equipment: str,
        manual_hits: list[RetrievalHit],
        case_hits: list[RetrievalHit],
        visual_asset: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        paths: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for hit in manual_hits + case_hits:
            key = (equipment or hit.equipment, hit.component, hit.fault_type)
            if key in seen:
                continue
            seen.add(key)
            paths.append(_hit_path(equipment, hit))
            if len(paths) >= 5:
                break
        if visual_asset and paths:
            visual_node = {
                "id": _node_id("visual", visual_asset["id"]),
                "label": visual_asset["filename"],
                "type": "VisualAsset",
            }
            paths[0]["nodes"].insert(0, visual_node)
            paths[0]["edges"].insert(
                0,
                {
                    "source": visual_node["id"],
                    "target": paths[0]["nodes"][1]["id"],
                    "relation": "OBSERVED_IN",
                },
            )
            paths[0]["path"].insert(0, visual_node["label"])
            paths[0]["relations"].insert(0, "OBSERVED_IN")
        return paths


class Neo4jGraphStore(SQLiteGraphStore):
    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__(conn, backend="neo4j")
        self._driver = None
        self._error = ""
        try:
            from neo4j import GraphDatabase  # type: ignore

            if not settings.neo4j_uri or not settings.neo4j_password:
                raise RuntimeError("NEO4J_URI or NEO4J_PASSWORD missing")
            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
            self._driver.verify_connectivity()
        except Exception as exc:  # noqa: BLE001
            self._driver = None
            self._error = str(exc)

    @property
    def connected(self) -> bool:
        return self._driver is not None

    def status(self) -> dict[str, Any]:
        if not self._driver:
            return {
                "backend": "neo4j",
                "connected": False,
                "reason": self._error,
                "node_count": 0,
                "edge_count": 0,
                "last_sync": "",
            }
        with self._driver.session(database=settings.neo4j_database) as session:
            node_count = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
            edge_count = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        return {
            "backend": "neo4j",
            "connected": True,
            "reason": "",
            "node_count": node_count,
            "edge_count": edge_count,
            "last_sync": "",
        }

    def rebuild(self) -> dict[str, Any]:
        if not self._driver:
            fallback = SQLiteGraphStore(self.conn, backend="sqlite_fallback", reason=self._error)
            return fallback.rebuild()
        records = collect_graph_records(self.conn)
        with self._driver.session(database=settings.neo4j_database) as session:
            session.run("MATCH (n) DETACH DELETE n")
            for node in records.nodes.values():
                session.run(
                    """
                    MERGE (n:KnowledgeNode {id: $id})
                    SET n.label = $label, n.type = $type
                    """,
                    node,
                )
            for source, target, relation in records.edges:
                session.run(
                    """
                    MATCH (s:KnowledgeNode {id: $source})
                    MATCH (t:KnowledgeNode {id: $target})
                    MERGE (s)-[r:RELATED {relation: $relation}]->(t)
                    """,
                    {"source": source, "target": target, "relation": relation},
                )
        return {
            "backend": "neo4j",
            "connected": True,
            "node_count": len(records.nodes),
            "edge_count": len(records.edges),
            "last_sync": datetime.utcnow().isoformat(timespec="seconds"),
        }


def get_graph_store(conn: sqlite3.Connection) -> SQLiteGraphStore:
    if settings.graph_backend == "neo4j":
        neo4j_store = Neo4jGraphStore(conn)
        if neo4j_store.connected:
            return neo4j_store
        return SQLiteGraphStore(conn, backend="sqlite_fallback", reason=neo4j_store._error)
    return SQLiteGraphStore(conn)
