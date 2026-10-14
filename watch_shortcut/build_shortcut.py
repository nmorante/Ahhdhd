"""Generate an unsigned 'Watch Log.shortcut'. Sign on a Mac before importing:
    shortcuts sign -m anyone -i "Watch Log.shortcut" -o "Watch Log signed.shortcut"
"""
import plistlib, uuid

actions = []

def act(ident, params):
    u = str(uuid.uuid4()).upper()
    params = {"UUID": u, **params}
    actions.append({"WFWorkflowActionIdentifier": ident, "WFWorkflowActionParameters": params})
    return u

def out(u, name):
    return {"Type": "ActionOutput", "OutputUUID": u, "OutputName": name}

def attach(u, name):
    return {"Value": out(u, name), "WFSerializationType": "WFTextTokenAttachment"}

def tokens(parts):
    """parts: list of str or (uuid, name). Builds a WFTextTokenString."""
    s, rng = "", {}
    for p in parts:
        if isinstance(p, str):
            s += p
        else:
            pos = len(s.encode("utf-16-le")) // 2
            rng[f"{{{pos}, 1}}"] = out(*p)
            s += "￼"
    return {"Value": {"string": s, "attachmentsByRange": rng},
            "WFSerializationType": "WFTextTokenString"}

def find_health(type_name):
    return act("is.workflow.actions.filter.health.quantity", {
        "WFContentItemFilter": {
            "Value": {
                "WFActionParameterFilterPrefix": 1,
                "WFContentPredicateBoundedDate": False,
                "WFActionParameterFilterTemplates": [
                    {"Property": "Type", "Operator": 4, "Removable": False,
                     "Values": {"Enumeration": {"Value": type_name,
                                "WFSerializationType": "WFStringSubstitutableState"}}},
                    {"Property": "Start Date", "Operator": 1002, "Removable": True,
                     "Values": {"Unit": 16, "Number": 1}},
                ],
            },
            "WFSerializationType": "WFContentPredicateTableTemplate",
        },
    })

def stat(src, op, name):
    u = act("is.workflow.actions.statistics", {
        "WFStatisticsOperation": op,
        "Input": attach(src, "Health Samples"),
        "CustomOutputName": name,
    })
    return (u, name)

metrics = [
    ("Steps", "Sum", "steps"),
    ("Walking + Running Distance", "Sum", "distance_km"),
    ("Active Energy", "Sum", "active_kcal"),
    ("Resting Energy", "Sum", "basal_kcal"),
    ("Exercise Minutes", "Sum", "exercise_min"),
    ("Resting Heart Rate", "Average", "resting_hr"),
    ("Heart Rate Variability", "Average", "hrv_ms"),
]
vals = {name: stat(find_health(t), op, name) for t, op, name in metrics}

date_u = act("is.workflow.actions.format.date", {
    "WFDateFormatStyle": "Custom",
    "WFDateFormat": "yyyy-MM-dd",
    "WFDate": {"Value": {"string": "￼", "attachmentsByRange": {"{0, 1}": {"Type": "CurrentDate"}}},
               "WFSerializationType": "WFTextTokenString"},
    "CustomOutputName": "date",
})

parts = ['{"date":"', (date_u, "date"), '"']
for _, _, name in metrics:
    parts += [f',"{name}":', vals[name]]
parts.append("}")
text_u = act("is.workflow.actions.gettext", {"WFTextActionText": tokens(parts)})

act("is.workflow.actions.file.append", {
    "WFFilePath": "watch_log/watch.jsonl",
    "WFInput": attach(text_u, "Text"),
    "WFAppendOnNewLine": True,
})

shortcut = {
    "WFWorkflowActions": actions,
    "WFWorkflowClientVersion": "2302.0.4",
    "WFWorkflowMinimumClientVersion": 900,
    "WFWorkflowMinimumClientVersionString": "900",
    "WFWorkflowIcon": {"WFWorkflowIconStartColor": 4282601983, "WFWorkflowIconGlyphNumber": 59511},
    "WFWorkflowImportQuestions": [],
    "WFWorkflowInputContentItemClasses": [],
    "WFWorkflowOutputContentItemClasses": [],
    "WFWorkflowTypes": [],
    "WFWorkflowHasShortcutInputVariables": False,
    "WFQuickActionSurfaces": [],
}

with open("Watch Log.shortcut", "wb") as f:
    plistlib.dump(shortcut, f, fmt=plistlib.FMT_BINARY)
print(f"wrote Watch Log.shortcut ({len(actions)} actions)")
