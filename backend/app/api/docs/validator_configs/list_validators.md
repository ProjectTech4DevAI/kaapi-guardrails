Lists validator configurations for an organization/project scope, with optional filtering.

Each result item is flattened:
- Base fields (`id`, `type`, `stage`, `on_fail_action`, `is_enabled`, scope ids, timestamps)
- Validator-specific config fields

Behavior notes:
- Filters are combined (logical AND) when multiple are provided.
- `ids` supports multi-value filtering.

Common failure cases:
- Invalid filter formats (for example malformed UUID in `ids`).
