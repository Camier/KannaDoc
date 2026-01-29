from typing import Dict, List, Optional
from collections import defaultdict, deque


class TreeNode:
    __slots__ = [
        "node_id",
        "node_type",
        "data",
        "children",
        "loop_info",
        "parents",
        "loop_next",
        "loop_parent",
        "condition",
        "loop_last",
        "loop_children",
        "debug_skip",
        "input_skip",
    ]
    _instances = {}

    def __new__(cls, node_id: str, node_type: str, data: Dict, condition=None):
        if node_id not in cls._instances:
            instance = super().__new__(cls)
            instance.node_id = node_id
            instance.node_type = node_type
            instance.data = data
            instance.children = []
            instance.loop_info = []
            instance.parents = []
            instance.loop_next = []
            instance.loop_parent = None
            instance.loop_children = []
            instance.loop_last = []
            instance.condition = condition
            instance.debug_skip = False
            instance.input_skip = False
            cls._instances[node_id] = instance
        return cls._instances[node_id]

    @classmethod
    def get_node(cls, node_id: str):
        return cls._instances.get(node_id)

    @classmethod
    def clear_instances(cls):
        cls._instances.clear()


class WorkflowGraph:
    def __init__(self, nodes: List[Dict], edges: List[Dict], start_node: str):
        TreeNode.clear_instances()
        self.nodes = {n["id"]: n for n in nodes}
        self.edges = edges
        self.root = TreeNode(start_node, "start", {"name": "Start"})
        self._build_graph(self.root, parent=None, current_loop_parent=None)
        self._validate_hierarchy()
        self._check_directed_cycles()

    def _find_edges(self, source: str) -> List[Dict]:
        return [e for e in self.edges if e.get("source") == source]

    def _build_graph(
        self,
        node: TreeNode,
        parent: Optional[TreeNode],
        current_loop_parent: Optional[TreeNode],
    ):
        node.loop_parent = current_loop_parent
        if current_loop_parent:
            current_loop_parent.loop_children.append(node)

        if parent and parent not in node.parents:
            node.parents.append(parent)

        for edge in self._find_edges(node.node_id):
            self._process_edge(node, edge, current_loop_parent)

    def _process_edge(
        self, node: TreeNode, edge: Dict, current_loop_parent: Optional[TreeNode]
    ):
        source_handle = edge.get("sourceHandle", "")
        target_id = edge["target"]
        target_node = TreeNode(
            target_id, self.nodes[target_id]["type"], self.nodes[target_id]["data"]
        )

        try:
            if source_handle == "":
                self._validate_normal_edge(node, target_node, current_loop_parent)
                self._add_child(node, target_node, current_loop_parent)
            elif source_handle.startswith("condition"):
                try:
                    condition_index = int(source_handle.split("-")[-1])
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid condition type: {source_handle}")
                self._validate_condition_edge(
                    node, target_node, current_loop_parent, condition_index
                )
                target_node.condition = condition_index
                self._add_child(node, target_node, current_loop_parent)
            elif source_handle == "loop_body":
                self._validate_loop_body_edge(node)
                self._add_loop_child(node, target_node)
            elif source_handle == "loop_next":
                self._validate_loop_next_edge(node, target_node)
                self._add_loop_exit(node, target_node)
            else:
                raise ValueError(f"Invalid edge type: {source_handle}")
        except ValueError as e:
            raise type(e)(
                f"Node {node.data['name']} -> {target_node.data['name']}: {str(e)}"
            ) from e

    def _validate_normal_edge(
        self,
        source: TreeNode,
        target: TreeNode,
        current_loop_parent: Optional[TreeNode],
    ):
        if target.loop_parent not in {None, current_loop_parent}:
            raise ValueError(
                f"Cross-hierarchy connection: {source.data['name']} "
                f"-> {target.data['name']}"
            )

    def _validate_condition_edge(
        self,
        source: TreeNode,
        target: TreeNode,
        current_loop_parent: Optional[TreeNode],
        condition_index: int,
    ):
        if source.node_type != "condition":
            raise ValueError("Condition edge used on non-condition node")
        if target.loop_parent not in {None, current_loop_parent}:
            raise ValueError(
                f"Cross-hierarchy connection: {source.data['name']} "
                f"-> {target.data['name']}"
            )

    def _validate_loop_body_edge(self, node: TreeNode):
        if node.node_type != "loop":
            raise ValueError("loop_body edge used on non-loop node")

    def _validate_loop_next_edge(self, node: TreeNode, target_node: TreeNode):
        if node.loop_parent != target_node:
            raise ValueError("loop_next edge does not point back to loop node")
        if node.node_type == "condition":
            raise ValueError("loop_next exit cannot be a condition node")
        if target_node.node_type != "loop":
            raise ValueError("loop_next edge used on non-loop node")
        if len(target_node.loop_next) >= 1:
            raise ValueError("Loop node can only have one loop_next exit")

    def _get_hierarchy_path(self, node: TreeNode) -> str:
        path = []
        current = node.loop_parent
        while current:
            path.append(current.data["name"])
            current = current.loop_parent
        return "->".join(reversed(path)) if path else "root"

    def _add_child(
        self,
        parent: TreeNode,
        child: TreeNode,
        current_loop_parent: Optional[TreeNode],
    ):
        if child not in parent.children:
            parent.children.append(child)
            self._build_graph(child, parent, current_loop_parent)

    def _add_loop_child(self, loop_node: TreeNode, child: TreeNode):
        if child not in loop_node.loop_info:
            loop_node.loop_info.append(child)
            if len(loop_node.loop_info) > 1:
                raise ValueError("Loop node can only have one loop_body entry")
            self._build_graph(child, None, loop_node)

    def _add_loop_exit(self, last_child_node: TreeNode, loop_node: TreeNode):
        if last_child_node not in loop_node.loop_last:
            loop_node.loop_last.append(last_child_node)

    def _validate_hierarchy(self):
        for node in TreeNode._instances.values():
            for child in node.children:
                if child.loop_parent != node.loop_parent:
                    raise ValueError(
                        f"Hierarchy break: {node.data['name']} -> {child.data['name']}"
                    )

    def _check_directed_cycles(self):
        visited = defaultdict(int)
        path = deque()
        path_name = deque()
        cycle = None
        cycle_name = None

        def dfs(current: TreeNode):
            nonlocal cycle, cycle_name
            if visited[current.node_id] == 1:
                cycle = list(path) + [current.node_id]
                cycle_name = list(path_name) + [current.data["name"]]
                raise ValueError("")
            if visited[current.node_id] == 2:
                return

            visited[current.node_id] = 1
            path.append(current.node_id)
            path_name.append(current.data["name"])

            for child in current.children + current.loop_info + current.loop_next:
                dfs(child)

            visited[current.node_id] = 2
            path.pop()
            path_name.pop()

        try:
            for node in TreeNode._instances.values():
                if visited[node.node_id] == 0:
                    dfs(node)
        except ValueError:
            if cycle_name:
                cycle_str = " -> ".join(cycle_name)
                raise ValueError(
                    f"Detected directed cycle: {cycle_str}. "
                    "Use loop nodes for iteration."
                )
