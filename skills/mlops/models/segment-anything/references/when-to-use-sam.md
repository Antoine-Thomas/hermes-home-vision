# When to use SAM

**Use SAM when:**
- Need to segment any object in images without task-specific training
- Building interactive annotation tools with point/box prompts
- Generating training data for other vision models
- Need zero-shot transfer to new image domains
- Building object detection/segmentation pipelines
- Processing medical, satellite, or domain-specific images

**Key features:**
- **Zero-shot segmentation**: Works on any image domain without fine-tuning
- **Flexible prompts**: Points, bounding boxes, or previous masks
- **Automatic segmentation**: Generate all object masks automatically
- **High quality**: Trained on 1.1 billion masks from 11 million images
- **Multiple model sizes**: ViT-B (fastest), ViT-L, ViT-H (most accurate)
- **ONNX export**: Deploy in browsers and edge devices

**Use alternatives instead:**
- **YOLO/Detectron2**: For real-time object detection with classes
- **Mask2Former**: For semantic/panoptic segmentation with categories
- **GroundingDINO + SAM**: For text-prompted segmentation
- **SAM 2**: For video segmentation tasks
