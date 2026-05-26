---
title: Image Generation Skill
trigger: visual_task, diagram_request, concept_visualization
author: PicoCloth
model: dall-e-3
---

# Image Generation Protocol

## When to Use
- User asks for diagrams, charts, or visual frameworks
- Complex concepts need visual explanation
- Marketing assets, slides, or presentation images
- Architecture diagrams or data flow visuals

## Workflow

1. **Clarify intent**
   - What style? (photorealistic, diagram, sketch, pixel art)
   - What aspect ratio? (1024x1024, 1792x1024, 1024x1792)
   - What must be included? What must be avoided?

2. **Craft prompt**
   - Be specific but concise (max 4000 chars for DALL-E 3)
   - Include style keywords: "professional diagram", "clean vector illustration", "architectural blueprint"
   - Add negative constraints: "no text", "no watermarks", "minimalist"

3. **Generate**
   - Call DALL-E 3 via OpenAI API
   - Request `hd` quality for professional use
   - Save to `shared/project/documents/images/`
   - Log generation metadata (prompt, model, cost) to fleet state

4. **Deliver**
   - Provide image URL + local path
   - Explain what the image shows
   - Offer iteration: "Want me to adjust X?"

## Example Prompts

| Use Case | Prompt |
|----------|--------|
| Architecture diagram | "Clean vector diagram of a microservices architecture with API gateway, 3 services, and database. Blue and white color scheme. No text labels. Professional technical illustration." |
| Growth funnel | "Professional funnel diagram showing 5 stages: Awareness → Interest → Desire → Action → Retention. Gradient from blue to green. Clean corporate style. No text." |
| Concept map | "Mind map style illustration centered on a glowing brain node with 6 connected sub-nodes. Dark background, neon connections. Futuristic, clean, no text." |

## Safety
- Never generate images of real people without consent
- Never generate harmful, illegal, or deceptive content
- Watermark all generated images with "AI-generated" metadata
