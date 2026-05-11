# Multimodal Image Evaluation Status

ready: `True`
manifest: `D:\30726\Desktop\竞赛目录\a1-maintenance-assistant\data\image_eval\fault_image_eval_manifest.csv`

## Gate

| Item | Value |
|---|---:|
| required_images | 30 |
| manifest_rows | 30 |
| available_images | 30 |
| approved_images | 30 |
| missing_images | 0 |

## Equipment Coverage

| Equipment | Rows | Available | Approved | Missing |
|---|---:|---:|---:|---:|
| `bearing` | 10 | 10 | 10 | 0 |
| `motor` | 10 | 10 | 10 | 0 |
| `pump` | 10 | 10 | 10 | 0 |

## Missing Resources

- None

## Raw Result

```json
{
  "exists": true,
  "manifest": "D:\\30726\\Desktop\\竞赛目录\\a1-maintenance-assistant\\data\\image_eval\\fault_image_eval_manifest.csv",
  "required_images": 30,
  "total": 30,
  "available_images": 30,
  "approved_images": 30,
  "missing_images": 0,
  "invalid_rows": [],
  "missing_columns": [],
  "by_equipment": {
    "motor": {
      "total": 10,
      "available": 10,
      "approved": 10,
      "missing": 0,
      "fault_types": {
        "overheat_damage": 1,
        "bearing_grease_seal": 1,
        "rotor_damage": 1,
        "motor_damage": 1,
        "motor_damage_closeup": 1,
        "motor_disassembly": 1,
        "motor_bearing_assembly": 1,
        "grease_seal_parts": 1,
        "bearing_mount": 1,
        "bearing_mount_inspection": 1
      }
    },
    "pump": {
      "total": 10,
      "available": 10,
      "approved": 10,
      "missing": 0,
      "fault_types": {
        "pump_seal_leak_failure": 1,
        "gland_packing": 1,
        "cavitation": 1,
        "cavitation_wear": 1,
        "cavitation_damage": 1,
        "cavitation_reference": 1,
        "mechanical_seal_parts": 1,
        "pump_seal_reference": 1,
        "erosion_corrosion": 2
      }
    },
    "bearing": {
      "total": 10,
      "available": 10,
      "approved": 10,
      "missing": 0,
      "fault_types": {
        "bearing_damage": 3,
        "damaged_motor_bearing": 2,
        "false_brinelling": 1,
        "fretting_corrosion": 1,
        "false_brinelling_test": 1,
        "fretting_false_brinelling": 1,
        "failed_bearing": 1
      }
    }
  },
  "missing_equipment": [],
  "missing_paths": [],
  "ready": true
}
```
