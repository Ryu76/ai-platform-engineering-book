"""Volume 09의 결정론적 State Reducer를 오프라인으로 확인한다."""
from ai_platform.graph import WorkflowEvent, reduce_events

existing_events = (WorkflowEvent(sequence=1, node="plan", detail="오프라인 계획"),)
local_node_updates = (
    WorkflowEvent(sequence=1, node="approval", detail="안전 작업 확인"),
    WorkflowEvent(sequence=2, node="execute", detail="오프라인 완료"),
)
merged_events = reduce_events(existing_events, local_node_updates)

print("events=" + " | ".join(event.node for event in merged_events))
print("sequences=" + " | ".join(str(event.sequence) for event in merged_events))
