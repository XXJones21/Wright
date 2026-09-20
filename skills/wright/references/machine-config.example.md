# Machine config

The conductor (`skills/wright/SKILL.md`, Step 0.5) reads this file before dispatching any subagent and substitutes the values into every dispatch prompt. This is the ONLY file where machine-specific literals belong. Copy it to `machine-config.md` beside it and edit the values; `machine-config.md` is gitignored.

| Field | Meaning | Default / this machine |
| --- | --- | --- |
| `UE_PROJECT_ROOT` | The Unreal project the run targets. Must contain the `.uproject` and the editor-generated `.mcp.json`. `--project` on the command overrides it. | `D:\UnrealProjects\Retrieval` |
| `RUNS_DIR` | Root for run folders (`<RUNS_DIR>/<slug>/plan.md`). | `<UE_PROJECT_ROOT>\wright\runs` |
| `TEXTURE_STAGING_DIR` | Where ComfyUI textures and their seamless/normal derivatives land before `TextureTools.import_file`. | `<UE_PROJECT_ROOT>\wright\textures` |
| `COMFY_TEXTURE_WORKFLOW` | comfy-local workflow name for seamless texture tiles. Confirm with `list_workflows`. | `scene_image_flux` |
| `COMFY_PLATE_WORKFLOW` | comfy-local workflow name for concept plates. | `scene_image_flux` |
| `GPS_MAX_CHARS` | Character cap for the PROJECT GPS section; truncation is announced, never silent. | `12000` |
| `DESIGN_DOCS` | Comma-separated paths handed to the reference investigator (game design document, slice brief). | `<UE_PROJECT_ROOT>\Documentation\GDD_Retrieval.md` |

## How this gets used
At Step 0.5 the skill reads `machine-config.md` (or this example if the copy is absent) and resolves every `<ue_project_root>`, `<runs_dir>`, `<texture_staging_dir>`, `<comfy_texture_workflow>`, `<comfy_plate_workflow>`, `<gps_max_chars>`, and `<design_docs>` placeholder in the dispatch templates. Subagents never hardcode these paths; they receive them resolved. If `UE_PROJECT_ROOT` cannot be resolved from either file or `--project`, the run stops at Step 0.5.
