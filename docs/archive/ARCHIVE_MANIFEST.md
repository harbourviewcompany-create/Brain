# Brain Current Thread Archive Manifest

This manifest records the ZIP package contents that need to be preserved in the repository.

Source ZIP path in the working environment: `/mnt/data/Brain_Compilation_Full_Current_Thread_Package.zip`

## Intended repo placement

| ZIP item | Intended repo path | Bytes | SHA-256 |
|---|---:|---:|---|
| Brain_Compilation_Full_Current_Thread.docx | docs/archive/Brain_Compilation_Full_Current_Thread.docx | 9,096,825 | 81807a40a7954c9bdb45b89b8422ac4d09cf6cd9da40bb3ecbf7d5af93e35ebc |
| Brain_Compilation_Full_Current_Thread.md | docs/archive/Brain_Compilation_Full_Current_Thread.md | 169,344 | fa780b956d80548e8e12575de6de8c45ba0ea51bdfffff27e83e27f0b55d9cee |
| Pasted text.txt | docs/archive/source/Pasted text.txt | 91,085 | b262f961ac46f7eae4fd7297a67c803daf404060031c3db6d7bdb7289e7ffb41 |
| step_by_step_process_overview.png | docs/archive/visuals/step_by_step_process_overview.png | 1,029,022 | af5ef6aea22d38f83b1a3b4e6e7a67a77614ffeec60d7372fddf9123d32ae6fb |
| brain_functions_vs._real_brain_anatomy.png | docs/archive/visuals/brain_functions_vs._real_brain_anatomy.png | 1,685,374 | e6c5294e2ea74bc988bd1b2e6144b52e76538557ccc39a138d1fa3f0fbc0e35d |
| a_high_detail_infographic_poster_on_a_dark_black_t.png | docs/archive/visuals/a_high_detail_infographic_poster_on_a_dark_black_t.png | 2,009,175 | b5cd31b78131c046c4f0fdb39815f7420e7246c81c373f7639166ca8afd203cf |
| brain_vs_ai_a_comparative_overview.png | docs/archive/visuals/brain_vs_ai_a_comparative_overview.png | 1,625,487 | 392d1b9e096c56b4469b15e745ec8e5125e40ba90da4ef6f91c202a4309d3758 |
| brain_architecture_vs_generic_ai_comparison.png | docs/archive/visuals/brain_architecture_vs_generic_ai_comparison.png | 1,431,189 | cac61a86a0ae35dce9da1c41218b2a9dc1cda072f1283e7f405ac4725f3b8f1c |
| comparing_ai_and_brain_architectures.png | docs/archive/visuals/comparing_ai_and_brain_architectures.png | 1,407,523 | 508360ec084f26757eb3848602ca74e69025df08730732249ed7591fc8c005d8 |
| Brain_Compilation_Full_Current_Thread_Package.zip | artifacts/Brain_Compilation_Full_Current_Thread_Package.zip | 18,545,024 | 5b17edc9e0bbc4d18b02bf83cae348c281ec5a84396e8f4eeb2fed53c5afb33c |

## Connector limitation encountered

The GitHub connector write actions accept literal string content or base64 string content. They do not read local `/mnt/data/...` file paths as file bytes unless an action is explicitly defined as a file-parameter action. The available GitHub create/update/blob actions are not file-parameter actions.

Do not treat this manifest as a substitute for the archive assets. The files listed above still need to be committed as actual repository blobs.
