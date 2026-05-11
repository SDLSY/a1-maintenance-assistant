# Multimodal Image Evaluation Status

ready: `False`
manifest: `D:\30726\Desktop\竞赛目录\a1-maintenance-assistant\data\image_eval\fault_image_eval_manifest.csv`

## Gate

| Item | Value |
|---|---:|
| required_images | 30 |
| manifest_rows | 30 |
| available_images | 0 |
| approved_images | 0 |
| missing_images | 30 |

## Equipment Coverage

| Equipment | Rows | Available | Approved | Missing |
|---|---:|---:|---:|---:|
| `bearing` | 10 | 0 | 0 | 10 |
| `motor` | 10 | 0 | 0 | 10 |
| `pump` | 10 | 0 | 0 | 10 |

## Missing Resources

missing_paths:
- `data/image_eval/images/motor_bearing_overheat_01.jpg`
- `data/image_eval/images/motor_bearing_overheat_02.jpg`
- `data/image_eval/images/motor_terminal_burn_01.jpg`
- `data/image_eval/images/motor_fan_blocked_01.jpg`
- `data/image_eval/images/motor_coupling_misalignment_01.jpg`
- `data/image_eval/images/motor_bearing_grease_contamination_01.jpg`
- `data/image_eval/images/motor_mount_loose_01.jpg`
- `data/image_eval/images/motor_insulation_crack_01.jpg`
- `data/image_eval/images/motor_seal_oil_leak_01.jpg`
- `data/image_eval/images/motor_rotor_rub_01.jpg`
- `data/image_eval/images/pump_mechanical_seal_leak_01.jpg`
- `data/image_eval/images/pump_gasket_leak_01.jpg`
- `data/image_eval/images/pump_cavitation_impeller_01.jpg`
- `data/image_eval/images/pump_bearing_overheat_01.jpg`
- `data/image_eval/images/pump_base_vibration_01.jpg`
- `data/image_eval/images/pump_coupling_guard_removed_01.jpg`
- `data/image_eval/images/pump_strainer_blocked_01.jpg`
- `data/image_eval/images/pump_corrosion_01.jpg`
- `data/image_eval/images/pump_oil_milk_01.jpg`
- `data/image_eval/images/pump_pipe_stress_01.jpg`
- `data/image_eval/images/bearing_outer_race_spalling_01.jpg`
- `data/image_eval/images/bearing_inner_race_pitting_01.jpg`
- `data/image_eval/images/bearing_cage_crack_01.jpg`
- `data/image_eval/images/bearing_grease_dark_01.jpg`
- `data/image_eval/images/bearing_rust_01.jpg`
- `data/image_eval/images/bearing_false_brinelling_01.jpg`
- `data/image_eval/images/bearing_overload_deformation_01.jpg`
- `data/image_eval/images/bearing_misalignment_wear_01.jpg`
- `data/image_eval/images/bearing_electrical_fluting_01.jpg`
- `data/image_eval/images/bearing_seal_damage_01.jpg`

## Raw Result

```json
{
  "exists": true,
  "manifest": "D:\\30726\\Desktop\\竞赛目录\\a1-maintenance-assistant\\data\\image_eval\\fault_image_eval_manifest.csv",
  "required_images": 30,
  "total": 30,
  "available_images": 0,
  "approved_images": 0,
  "missing_images": 30,
  "invalid_rows": [],
  "missing_columns": [],
  "by_equipment": {
    "motor": {
      "total": 10,
      "available": 0,
      "approved": 0,
      "missing": 10,
      "fault_types": {
        "bearing_overheat": 2,
        "electrical_terminal_burn": 1,
        "cooling_blocked": 1,
        "coupling_misalignment": 1,
        "grease_contamination": 1,
        "mount_loose": 1,
        "insulation_crack": 1,
        "seal_oil_leak": 1,
        "rotor_rub": 1
      }
    },
    "pump": {
      "total": 10,
      "available": 0,
      "approved": 0,
      "missing": 10,
      "fault_types": {
        "mechanical_seal_leak": 1,
        "gasket_leak": 1,
        "cavitation": 1,
        "bearing_overheat": 1,
        "base_vibration": 1,
        "guard_missing": 1,
        "strainer_blocked": 1,
        "corrosion": 1,
        "oil_emulsification": 1,
        "pipe_stress": 1
      }
    },
    "bearing": {
      "total": 10,
      "available": 0,
      "approved": 0,
      "missing": 10,
      "fault_types": {
        "outer_race_spalling": 1,
        "inner_race_pitting": 1,
        "cage_crack": 1,
        "grease_degradation": 1,
        "corrosion": 1,
        "false_brinelling": 1,
        "overload_deformation": 1,
        "misalignment_wear": 1,
        "electrical_fluting": 1,
        "seal_damage": 1
      }
    }
  },
  "missing_equipment": [],
  "missing_paths": [
    "data/image_eval/images/motor_bearing_overheat_01.jpg",
    "data/image_eval/images/motor_bearing_overheat_02.jpg",
    "data/image_eval/images/motor_terminal_burn_01.jpg",
    "data/image_eval/images/motor_fan_blocked_01.jpg",
    "data/image_eval/images/motor_coupling_misalignment_01.jpg",
    "data/image_eval/images/motor_bearing_grease_contamination_01.jpg",
    "data/image_eval/images/motor_mount_loose_01.jpg",
    "data/image_eval/images/motor_insulation_crack_01.jpg",
    "data/image_eval/images/motor_seal_oil_leak_01.jpg",
    "data/image_eval/images/motor_rotor_rub_01.jpg",
    "data/image_eval/images/pump_mechanical_seal_leak_01.jpg",
    "data/image_eval/images/pump_gasket_leak_01.jpg",
    "data/image_eval/images/pump_cavitation_impeller_01.jpg",
    "data/image_eval/images/pump_bearing_overheat_01.jpg",
    "data/image_eval/images/pump_base_vibration_01.jpg",
    "data/image_eval/images/pump_coupling_guard_removed_01.jpg",
    "data/image_eval/images/pump_strainer_blocked_01.jpg",
    "data/image_eval/images/pump_corrosion_01.jpg",
    "data/image_eval/images/pump_oil_milk_01.jpg",
    "data/image_eval/images/pump_pipe_stress_01.jpg",
    "data/image_eval/images/bearing_outer_race_spalling_01.jpg",
    "data/image_eval/images/bearing_inner_race_pitting_01.jpg",
    "data/image_eval/images/bearing_cage_crack_01.jpg",
    "data/image_eval/images/bearing_grease_dark_01.jpg",
    "data/image_eval/images/bearing_rust_01.jpg",
    "data/image_eval/images/bearing_false_brinelling_01.jpg",
    "data/image_eval/images/bearing_overload_deformation_01.jpg",
    "data/image_eval/images/bearing_misalignment_wear_01.jpg",
    "data/image_eval/images/bearing_electrical_fluting_01.jpg",
    "data/image_eval/images/bearing_seal_damage_01.jpg"
  ],
  "ready": false
}
```
