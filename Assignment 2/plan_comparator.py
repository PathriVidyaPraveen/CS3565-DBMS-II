def normalize_plan(plan):
    # extract only node types for comparison
    nodes = []

    def traverse(node):
        nodes.append(node["Node Type"])
        if "Plans" in node:
            for p in node["Plans"]:
                traverse(p)

    traverse(plan)
    return nodes


def compare_plans(plan1, plan2):
    return normalize_plan(plan1) == normalize_plan(plan2)
