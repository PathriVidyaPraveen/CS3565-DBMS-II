import json

def load_clean_json(file):
    with open(file, "r") as f:
        text = f.read()

    start = text.find('[')
    end = text.rfind(']') + 1

    json_text = text[start:end]

    return json.loads(json_text)


def extract_physical_operator_tree(plan):

    node_type = plan["Node Type"]

    children = []

    if "Plans" in plan:
        for child in plan["Plans"]:
            children.append(extract_physical_operator_tree(child))

    return (node_type, children)


def compare_plans(plan1, plan2):

    tree1 = extract_physical_operator_tree(plan1[0]["Plan"])
    tree2 = extract_physical_operator_tree(plan2[0]["Plan"])

    return tree1 == tree2


plan_files = [
    "query1.json",
    "query2.json"
]

for i in range(len(plan_files)):
    for j in range(i + 1, len(plan_files)):

        plan1 = load_clean_json(plan_files[i])
        plan2 = load_clean_json(plan_files[j])

        if compare_plans(plan1, plan2):
            print(f"{plan_files[i]} vs {plan_files[j]} : YES")
        else:
            print(f"{plan_files[i]} vs {plan_files[j]} : NO")