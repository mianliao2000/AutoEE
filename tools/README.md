# AutoEE Tool Adapters

These adapters define stable call boundaries for future external tools. v1 does
not call real distributor, EDA, firmware, or lab systems. Functions return
`not_configured`, `missing`, `dry_run`, or `blocked` so the agent can plan and
evaluate workflows without faking results.

Risky adapters must use `autoee_demo.core.safety.check_approval` before any real
manufacturing, firmware flashing, high-voltage, or high-current operation.
