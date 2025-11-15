from max_os.core.intent import Intent
from max_os.core.planner import IntentPlanner, KeywordRule


def test_keyword_rule_match():
    planner = IntentPlanner([KeywordRule("deploy", "dev.deploy", "Deploy apps", "keyword")])
    intent: Intent = planner.plan("Please deploy the dashboard")
    assert intent.name == "dev.deploy"
    assert intent.to_context()["keyword"] == "deploy"


def test_default_intent():
    planner = IntentPlanner([])
    intent = planner.plan("nonsense question")
    assert intent.name == "system.general"
    assert intent.confidence < 0.5
