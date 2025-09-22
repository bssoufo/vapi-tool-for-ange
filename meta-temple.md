#### Strategy 3: The "Meta-Template" or Enhanced Squad Template (Recommended)

This strategy extends your highly successful template pattern. We enhance the squad template to include a manifest that defines the assistants it depends on. The bootstrap command then uses this manifest to orchestrate the creation of all required components.

*   **Command:** `vapi-manager squad bootstrap <squad_name> --template <template_name> [--deploy]`
*   **Action:**
    1.  The command looks for a `manifest.yaml` inside the squad template directory (e.g., `templates/squads/dental_clinic_squad/manifest.yaml`).
    2.  This manifest lists the required assistants and which assistant templates they should be built from.
    3.  The bootstrap process reads the manifest and programmatically runs the logic for `file init` for each assistant.
    4.  It then runs the logic for `squad init`, automatically passing the list of newly created assistant names.
    5.  If the `--deploy` flag is used, it proceeds to run `file create` for each assistant and finally `squad create` for the squad, respecting the dependency order.
*   **Pros:**
    *   **Architecturally Consistent:** This is the most natural extension of your existing architecture. It elevates the "squad template" to a
 "system blueprint".
    *   **Leverages Existing Code:** It reuses the logic from `TemplateManager` and `SquadTemplateManager`.
    *   **Highly Reusable:** A single command (`squad bootstrap`) can stamp out entire, complex, multi-assistant systems in a reproducible way.
    *   **Declarative & Discoverable:** The dependencies are clearly declared within the template itself, making the system self-documenting.
*   **Cons:**
    *   Requires adding a new concept (the `manifest.yaml`) and a new orchestration layer (`BootstrapManager`).

---

### 3. Recommended Strategy & Implementation Plan

**I strongly recommend Strategy 3: The "Meta-Template" Approach.** It is the most robust, scalable, and architecturally consistent option. It turns your squad templates into powerful, reusable blueprints for entire conversational
AI systems.

Here is a detailed implementation plan:

#### A. New Command Structure

Define a new, high-level `bootstrap` command for squads in `vapi_manager/cli/simple_cli.py`.

```bash
# Initialize all local files for a full squad system
vapi-manager squad bootstrap dental_reception --template dental_clinic_squad

# Initialize AND deploy all components to an environment
vapi-manager squad bootstrap dental_reception --template dental_clinic_squad --deploy --env development
```

#### B. Enhanced Squad Template Structure

Add a `manifest.yaml` file to your squad templates.

```
templates/squads/
└── dental_clinic_squad/
    ├── manifest.yaml           # <-- NEW: Defines the assistants in the squad
    ├── squad.yaml
    ├── members.yaml
    ├── overrides/
    └── routing/
```

**Example `manifest.yaml`:**
This file declares the assistants that make up the squad.

```yaml
# templates/squads/dental_clinic_squad/manifest.yaml

description: "A complete dental clinic reception system with three specialized assistants for scheduling, triage, and billing."

# Assistants required by this squad blueprint.
# The bootstrap command will create these assistants first.
assistants:
  - name: "scheduler_bot"
    template: "vicky_dental_clinic" # Uses an assistant template from templates/
    role: "Handles new appointment scheduling."

  - name: "triage_assistant"
    template: "medical_triage" # Assumes a 'medical_triage' assistant template exists
    role: "Assesses medical urgency and answers health questions."

  - name: "billing_assistant"
    template: "billing_support" # Assumes a 'billing_support' assistant template exists
    role: "Handles payments, insurance, and billing inquiries."
```

#### C. Implementation Steps

1.  **Create a `BootstrapManager` Class:**
    *   Create a new file: `vapi_manager/core/bootstrap_manager.py`.
    *   This class will orchestrate the entire process. It will use instances of `TemplateManager` (for assistants) and `SquadTemplateManager`.

2.  **Implement the Bootstrap Logic:**
    *   The `BootstrapManager.run()` method will be the core.
    *   **Parse Manifest:** It will first load the `manifest.yaml` from the chosen squad template.
    *   **Initialize Assistants:** It will iterate through the `assistants` list in the manifest and call `template_manager.init_assistant()` for each one, creating their files in the `assistants/` directory.
    *   **Initialize Squad:** It will then call `squad_template_manager.initialize_squad()`, passing the list of assistant names it just created.
    *   **Handle Deployment (`--deploy`):**
        *   If the `--deploy` flag is present, it will then call the `create_assistant()` function for each assistant.
        *   After all assistants are successfully deployed, it will call `create_squad()` to deploy the final squad. This logic must be sequential and handle potential failures gracefully.

3.  **Integrate into the CLI (`simple_cli.py`):**
    *   Add the new `squad bootstrap` subparser and its arguments.
    *   The command handler will instantiate `BootstrapManager` and call its `run` method, passing the necessary arguments. The handler must be `async` to support the deployment steps.

4.  **Create Necessary Assistant Templates:**
    *   To make the `dental_clinic_squad` bootstrap work, you would need to ensure that assistant templates like `medical_triage` and `billing_support` exist in the `templates/` directory, alongside the existing `vicky_dental_clinic` template.

This approach provides a powerful, clean, and scalable way to manage the lifecycle of your entire multi-assistant systems while staying true to the excellent architectural patterns you've already
established.

================================================================================