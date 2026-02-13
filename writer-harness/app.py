"""Streamlit web UI for the Writing Harness."""

import os
import yaml
import streamlit as st
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: resolve workspace root BEFORE importing harness internals so the
# settings singleton picks up any env-var override we set here.
# ---------------------------------------------------------------------------
WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "./workspace"))
os.environ.setdefault("WORKSPACE_ROOT", str(WORKSPACE_ROOT))

from harness.config import Settings
from harness.models import ContinuityLedger, LintViolation
from harness.pipelines.draft import draft_scene, load_continuity_ledger, extract_seed_text
from harness.pipelines.revise import revise_draft
from harness.lint.rules import load_style_rules, load_banned_phrases
from harness.lint.style import lint_style
from harness.lint.continuity import lint_continuity
from harness.cli import create_workspace

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Writing Harness", page_icon="\u270E", layout="wide")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_settings() -> Settings:
    """Build a Settings object from sidebar values + env."""
    provider = st.session_state.get("provider", "anthropic")
    api_key = st.session_state.get("api_key", "")
    model = st.session_state.get("model_name", "claude-3-5-sonnet-20241022")
    max_tokens = st.session_state.get("max_tokens", 4000)

    env_overrides: dict = {
        "provider": provider,
        "model_name": model,
        "max_tokens": max_tokens,
        "workspace_root": WORKSPACE_ROOT,
    }
    if provider == "anthropic":
        env_overrides["anthropic_api_key"] = api_key
    else:
        env_overrides["openai_api_key"] = api_key

    return Settings(**env_overrides)


def _apply_settings(s: Settings):
    """Monkey-patch the module-level settings so pipelines pick it up."""
    import harness.config as _cfg
    _cfg.settings = s


def list_scenes() -> list[Path]:
    scenes_dir = WORKSPACE_ROOT / "scenes"
    if not scenes_dir.exists():
        return []
    return sorted(scenes_dir.glob("*.md"))


def list_outputs() -> list[Path]:
    output_dir = WORKSPACE_ROOT / "outputs"
    if not output_dir.exists():
        return []
    return sorted(output_dir.glob("*.md"))


def render_violations(violations: list[LintViolation], label: str):
    if not violations:
        st.success(f"No {label} violations.")
        return
    for v in violations:
        icon = "\u274C" if v.severity == "error" else "\u26A0\uFE0F"
        line_info = f" (line {v.line_number})" if v.line_number else ""
        st.markdown(f"{icon} **{v.severity.upper()}**{line_info}: {v.message}")
        if v.context:
            st.caption(f"> {v.context}")


# ---------------------------------------------------------------------------
# Sidebar: provider settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Settings")

    st.selectbox("Provider", ["anthropic", "openai"], key="provider")

    default_key = os.environ.get(
        "ANTHROPIC_API_KEY", os.environ.get("OPENAI_API_KEY", "")
    )
    st.text_input("API Key", value=default_key, type="password", key="api_key")

    default_model = (
        "claude-3-5-sonnet-20241022"
        if st.session_state.get("provider", "anthropic") == "anthropic"
        else "gpt-4"
    )
    st.text_input("Model", value=default_model, key="model_name")
    st.number_input("Max tokens", min_value=256, max_value=16384, value=4000, key="max_tokens")

    st.divider()
    st.caption(f"Workspace: `{WORKSPACE_ROOT.resolve()}`")

    if st.button("Initialize workspace"):
        create_workspace(WORKSPACE_ROOT)
        st.success("Workspace initialized.")

# Apply settings globally so pipeline imports use them.
_apply_settings(get_settings())

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_write, tab_draft, tab_revise, tab_lint, tab_config, tab_outputs = st.tabs(
    ["New Scene", "Draft", "Revise", "Lint", "Config", "Outputs"]
)

# ---- New Scene -----------------------------------------------------------
with tab_write:
    st.subheader("Create & edit a scene")

    title = st.text_input("Scene title", value="Untitled Scene")
    if st.button("Create scene"):
        scenes_dir = WORKSPACE_ROOT / "scenes"
        scenes_dir.mkdir(parents=True, exist_ok=True)
        existing = list(scenes_dir.glob("*.md"))
        next_num = len(existing) + 1
        scene_path = scenes_dir / f"{next_num:04d}_scene.md"

        state_path = WORKSPACE_ROOT / "state.yaml"
        ledger = load_continuity_ledger(state_path)

        header = (
            f"<!--\nCURRENT STATE (from state.yaml):\n"
            f"Location: {ledger.location_current}\n"
            f"Time: {ledger.time_of_day} | {ledger.date_or_day_count} | +{ledger.elapsed_time_since_last_scene}\n"
            f"Present: {', '.join(ledger.who_present)}\n"
            f"Goal: {ledger.scene_goal}\n"
            f"Tone: {ledger.tone_profile}\n"
            f"-->\n\n"
            f"# Scene {next_num:04d} — {title}\n\n"
        )
        scene_path.write_text(header)
        st.success(f"Created `{scene_path.name}`")
        st.rerun()

    # List existing scenes for editing
    scenes = list_scenes()
    if scenes:
        chosen = st.selectbox("Edit scene", scenes, format_func=lambda p: p.name)
        content = chosen.read_text()
        edited = st.text_area("Scene content", value=content, height=400, key=f"edit_{chosen.name}")
        if st.button("Save", key=f"save_{chosen.name}"):
            chosen.write_text(edited)
            st.success("Saved.")

# ---- Draft ---------------------------------------------------------------
with tab_draft:
    st.subheader("Generate a draft")

    scenes = list_scenes()
    if not scenes:
        st.info("No scenes yet. Create one in the **New Scene** tab.")
    else:
        scene_choice = st.selectbox("Scene file", scenes, format_func=lambda p: p.name, key="draft_scene")
        lore_k = st.slider("Lore snippets (k)", 0, 20, 8)
        no_lore = st.checkbox("Disable lore retrieval")

        if st.button("Draft scene"):
            if not st.session_state.get("api_key"):
                st.error("Enter your API key in the sidebar first.")
            else:
                with st.spinner("Drafting (calling LLM)..."):
                    try:
                        result = draft_scene(
                            scene_choice,
                            WORKSPACE_ROOT,
                            lore_k=lore_k,
                            use_lore=not no_lore,
                        )

                        # Save outputs
                        scene_num = scene_choice.stem.split("_")[0]
                        output_dir = WORKSPACE_ROOT / "outputs"
                        output_dir.mkdir(exist_ok=True)

                        draft_path = output_dir / f"{scene_num}_scene_draft.md"
                        draft_path.write_text(result["draft_text"])

                        st.success(f"Draft saved to `{draft_path.name}`")
                        st.markdown("### Draft")
                        st.markdown(result["draft_text"])

                        col1, col2 = st.columns(2)
                        with col1:
                            render_violations(result["style_violations"], "style")
                        with col2:
                            render_violations(result["continuity_violations"], "continuity")
                    except Exception as e:
                        st.error(f"Draft failed: {e}")

# ---- Revise --------------------------------------------------------------
with tab_revise:
    st.subheader("Revise a draft")

    drafts = [p for p in list_outputs() if "draft" in p.name]
    if not drafts:
        st.info("No drafts yet. Generate one in the **Draft** tab.")
    else:
        draft_choice = st.selectbox("Draft file", drafts, format_func=lambda p: p.name, key="revise_draft")
        strict = st.checkbox("Strict mode (fail if violations remain)")

        # Show current draft
        with st.expander("Preview draft"):
            st.markdown(draft_choice.read_text())

        if st.button("Revise draft"):
            if not st.session_state.get("api_key"):
                st.error("Enter your API key in the sidebar first.")
            else:
                with st.spinner("Revising (calling LLM)..."):
                    try:
                        draft_text = draft_choice.read_text()
                        result = revise_draft(draft_text, WORKSPACE_ROOT)

                        scene_num = draft_choice.stem.split("_")[0]
                        output_dir = WORKSPACE_ROOT / "outputs"

                        final_path = output_dir / f"{scene_num}_scene_out.md"
                        final_path.write_text(result["revised_text"])

                        st.success(f"Revised draft saved to `{final_path.name}`")
                        st.markdown("### Revised text")
                        st.markdown(result["revised_text"])

                        col1, col2 = st.columns(2)
                        with col1:
                            render_violations(result["style_violations"], "style")
                        with col2:
                            render_violations(result["continuity_violations"], "continuity")

                        remaining = len(result["style_violations"]) + len(result["continuity_violations"])
                        if strict and remaining > 0:
                            st.error(f"Strict mode: {remaining} violation(s) remain.")
                    except Exception as e:
                        st.error(f"Revise failed: {e}")

# ---- Lint ----------------------------------------------------------------
with tab_lint:
    st.subheader("Lint any text")

    lint_source = st.radio("Source", ["Paste text", "Choose file"], horizontal=True)

    text_to_lint = ""
    if lint_source == "Paste text":
        text_to_lint = st.text_area("Text to lint", height=300, key="lint_paste")
    else:
        all_files = list_scenes() + list_outputs()
        if all_files:
            lint_file = st.selectbox("File", all_files, format_func=lambda p: p.name, key="lint_file")
            text_to_lint = lint_file.read_text()
            with st.expander("File contents"):
                st.text(text_to_lint)
        else:
            st.info("No files in workspace yet.")

    if st.button("Run lint") and text_to_lint:
        state_path = WORKSPACE_ROOT / "state.yaml"
        ledger = load_continuity_ledger(state_path)

        banned_path = WORKSPACE_ROOT / "banned_phrases.yaml"
        banned = load_banned_phrases(banned_path)

        style_v = lint_style(text_to_lint, banned, scene_location=ledger.location_current)
        cont_v = lint_continuity(text_to_lint, ledger)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Style")
            render_violations(style_v, "style")
        with col2:
            st.markdown("### Continuity")
            render_violations(cont_v, "continuity")

# ---- Config --------------------------------------------------------------
with tab_config:
    st.subheader("Edit configuration files")

    config_files = {
        "state.yaml": WORKSPACE_ROOT / "state.yaml",
        "style_rules.yaml": WORKSPACE_ROOT / "style_rules.yaml",
        "banned_phrases.yaml": WORKSPACE_ROOT / "banned_phrases.yaml",
    }

    cfg_choice = st.selectbox("Config file", list(config_files.keys()), key="cfg_select")
    cfg_path = config_files[cfg_choice]

    if cfg_path.exists():
        raw = cfg_path.read_text()
        edited_cfg = st.text_area("YAML content", value=raw, height=500, key=f"cfg_{cfg_choice}")
        if st.button("Save config", key="save_cfg"):
            # Validate YAML before saving
            try:
                yaml.safe_load(edited_cfg)
                cfg_path.write_text(edited_cfg)
                st.success(f"Saved `{cfg_choice}`.")
            except yaml.YAMLError as e:
                st.error(f"Invalid YAML: {e}")
    else:
        st.warning(f"`{cfg_choice}` does not exist. Run **Initialize workspace** in the sidebar first.")

# ---- Outputs -------------------------------------------------------------
with tab_outputs:
    st.subheader("View outputs")

    outputs = list_outputs()
    if not outputs:
        st.info("No outputs yet.")
    else:
        out_choice = st.selectbox("Output file", outputs, format_func=lambda p: p.name, key="out_select")
        st.markdown(f"**{out_choice.name}**")
        st.markdown(out_choice.read_text())
