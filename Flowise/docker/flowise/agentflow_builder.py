"""Monta agentflow compativel com Flowise latest (inputParams + agentModelConfig)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

FLOWISE_ROOT = Path(__file__).resolve().parents[2]
MARKETPLACE_TEMPLATE = (
    FLOWISE_ROOT / "packages" / "server" / "marketplaces" / "agentflowsv2" / "Simple RAG.json"
)


def _find_node(template: dict, name: str) -> dict:
    for node in template.get("nodes", []):
        if node.get("data", {}).get("name") == name:
            return copy.deepcopy(node)
    raise ValueError(f"No node named {name!r} in template {MARKETPLACE_TEMPLATE}")


def _custom_tool_entry(tool_id: str) -> dict:
    """Custom tools do projeto devem usar o no built-in customTool (nao o nome direto)."""
    return {
        "agentSelectedTool": "customTool",
        "agentSelectedToolRequiresHumanInput": "",
        "agentSelectedToolConfig": {
            "selectedTool": tool_id,
            "agentSelectedTool": "customTool",
        },
    }


def build_agentflow(
    *,
    label: str,
    system_message: str,
    tool_ids: tuple[str, ...],
    model_config: dict[str, Any],
    agent_model: str,
    memory_window: int = 2,
    enable_memory: bool = False,
) -> dict:
    if not MARKETPLACE_TEMPLATE.is_file():
        raise FileNotFoundError(f"Template nao encontrado: {MARKETPLACE_TEMPLATE}")

    template = json.loads(MARKETPLACE_TEMPLATE.read_text(encoding="utf-8"))
    start = _find_node(template, "startAgentflow")
    agent = _find_node(template, "agentAgentflow")

    start["id"] = "startAgentflow_0"
    start["position"] = {"x": 100, "y": 120}
    start["data"]["id"] = "startAgentflow_0"
    start["data"]["inputs"] = {
        "startInputType": "chatInput",
        "formTitle": "",
        "formDescription": "",
        "formInputTypes": "",
        "startEphemeralMemory": "",
        "startState": "",
        "startPersistState": "",
    }

    agent["id"] = "agentAgentflow_0"
    agent["position"] = {"x": 420, "y": 120}
    data = agent["data"]
    data["id"] = "agentAgentflow_0"
    data["label"] = label

    cfg = dict(model_config)
    cfg["agentModel"] = agent_model

    data["inputs"] = {
        "agentModel": agent_model,
        "agentMessages": [{"role": "system", "content": system_message}],
        "agentTools": [_custom_tool_entry(tool_id) for tool_id in tool_ids] if tool_ids else "",
        "agentKnowledgeDocumentStores": [],
        "agentKnowledgeVSEmbeddings": "",
        "agentEnableMemory": enable_memory,
        "agentMemoryType": "windowSize" if enable_memory else "",
        "agentMemoryWindowSize": str(memory_window) if enable_memory else "",
        "agentUserMessage": "",
        "agentReturnResponseAs": "assistantMessage",
        "agentUpdateState": "",
        "agentStructuredOutput": "",
        "agentModelConfig": cfg,
    }

    return {
        "nodes": [start, agent],
        "edges": [
            {
                "id": "edge_start_agent",
                "source": "startAgentflow_0",
                "target": "agentAgentflow_0",
                "type": "agentFlow",
                "data": {"sourceColor": "#7EE787", "targetColor": "#4DD0E1"},
            }
        ],
    }
