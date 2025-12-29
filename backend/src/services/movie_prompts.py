"""
Movie Prompt Templates
电影工作流的所有Prompt模板集中管理
"""

class MoviePromptTemplates:
    """电影工作流Prompt模板管理器"""
    
    # 场景提取Prompt
    SCENE_EXTRACTION = """你是一名国际获奖级的电影编剧与导演，擅长将长篇小说章节转化为可直接用于电影制作与视频生成的结构化电影场景数据。

你的任务是：
**将以下小说章节拆分为多个电影场景（Scene），并为每一个场景生成高度具体、信息密度极高的电影级场景描述，同时标注该场景中出现的角色名称。**

---

## 【强约束规则（必须严格遵守）】

1. 你【不能】创造任何新角色  
2. 你【只能】使用我提供的「已存在角色列表」中的角色名字,角色名字必须完全一致，如 `梅露希亚 (Melusia)` 必须返回`梅露希亚 (Melusia)` ,不允许返回 `梅露希亚`
3. 场景中的 `characters` 只表示"出现的角色名字"，不区分主次  
4. 若某个场景没有任何角色出现，`characters` 必须为 `[]`  
5. 禁止在 JSON 中输出任何解释、注释、Markdown、代码块标记或多余文字  

---

## 已存在角色列表（只能从这里选择）：
{characters}

---

## 【输出格式（必须严格遵守）】

你必须 **只输出 JSON**，结构如下：

{{
  "scenes": [
    {{
      "order_index": 1,
      "scene": "高密度电影场景描述（见下方写作规范）",
      "characters": ["角色名1", "角色名2"]
    }}
  ]
}}

---

## 【Scene 字段写作规范（极其重要）】

`scene` 字段不是摘要，而是一段 **可直接被"看见"的电影文本**，必须尽可能详细、具体、连续，信息密度要高。

每一个 Scene 的描述应尽量包含以下内容（不需要显式分点）：

- **环境与空间**：地点、地形、建筑、天气、光线、时间感
- **声音要素**：环境音、脚步声、金属声、风声、雨声等
- **角色行动**：具体的肢体动作、位置变化、互动过程
- **冲突与张力**：对峙、追逐、威胁、犹豫、失控、爆发
- **对话内容**：重要对话直接写入，用引号标出，可适度精炼但必须保留原意
- **情绪呈现方式**：通过动作、语气、停顿、行为体现，禁止心理独白

Scene 描述应接近"剧本 + 文学描写"的融合，但始终以 **镜头可见内容** 为核心。

---

## 【场景拆分原则】

1. 一个 Scene 必须对应一个明确的时间与空间  
2. 当地点或时间发生明显变化时，必须拆分为新的 Scene  
3. 动作密集或冲突激烈的段落可以写得更长、更细  
4. 不写分镜、不写镜头语言、不写摄影术语  
5. 保持电影叙事节奏，避免整章只有一个 Scene  

---

## 【示例（仅用于理解信息密度与风格，不要照抄内容）】

{{
  "scenes": [
    {{
      "order_index": 1,
      "scene": "暴雨在夜色中倾泻而下，城墙外的碎石路被雨水冲刷成一条条反光的沟壑。城门半掩，腐朽的木门在狂风中不断撞击石框，发出沉闷的回响。阿尔德里克站在城门内侧，盔甲破损严重，左肩的铁甲已经裂开，鲜血顺着雨水缓慢流淌。他一手扶着城墙稳住身体，另一手紧握长剑，剑尖垂地，随着呼吸轻微颤抖。远处传来规律而沉重的脚步声，火把的光在雨幕中逐渐逼近。梅露希亚从队伍前方走出，停在城门外数步之遥，抬头说道："我以为你已经死在北境了。"阿尔德里克沉默片刻，将长剑重新提起，低声回应："我本来也希望如此。"风雨在两人之间翻涌，对峙的张力在城门内外不断积累。",
      "characters": ["阿尔德里克", "梅露希亚"]
    }},
    {{
      "order_index": 2,
      "scene": "黎明前的荒野一片死寂，薄雾贴着地面缓慢流动。焦黑的战旗倒插在泥土中，断裂的兵器散落四周，金属表面还残留着未干的血迹。风吹过草丛，发出低沉而空洞的声响，远处的乌鸦偶尔发出嘶哑的鸣叫。画面中没有任何角色出现，只剩下一场大战结束后的荒凉与空虚。",
      "characters": []
    }}
  ]
}}

---

## 【待改编小说章节】：
{text}
"""

    @classmethod
    def get_scene_extraction_prompt(cls, characters: str, text: str) -> str:
        """
        获取场景提取Prompt
        
        Args:
            characters: JSON格式的角色列表
            text: 小说章节内容
            
        Returns:
            str: 格式化后的prompt
        """
        return cls.SCENE_EXTRACTION.format(characters=characters, text=text)

    # 分镜提取Prompt
    SHOT_EXTRACTION = """你是一名国际获奖级的电影导演与分镜设计师，擅长将电影场景拆分为**可直接生成固定 8 秒视频的分镜头（Shot）**。

你的任务是：
**将以下电影场景拆分为多个 Shot，并为每一个 Shot 生成高度具体、可被“首尾帧锁定”的视觉画面描述，同时标注该 Shot 中出现的角色名称。**

---

## 【核心模型适配原则（必须严格理解并遵守）】

* **每一个 Shot = 一个固定 8 秒的视频**
* 视频模型仅使用：

  * Shot 的 **起始画面状态（首帧）**
  * Shot 的 **结束画面状态（尾帧）**
* 中间 8 秒内容由模型进行**连续视觉插值**

因此：

* 每一个 Shot 的描述中，必须 **隐含清晰的起始状态与结束状态**
* 所有关键动作结果、情绪落点，**必须体现在 Shot 末尾的可见画面**
* 禁止依赖“中途发生但最终画面不可见”的叙事变化

---

## 【强约束规则（必须严格遵守）】

1. 你【不能】创造任何新角色
2. 你【只能】使用我提供的「已存在角色列表」中的角色名字

   * 名字必须完全一致（如 `梅露希亚 (Melusia)`）
3. `characters` 字段 **只表示该 Shot 中出现的角色名字列表**，不区分主次
4. 若某个 Shot 中没有任何角色出现，`characters` 必须为 `[]`
5. **只输出 JSON**，禁止输出任何解释、注释、Markdown、代码块或多余文本

---

## 【已存在角色列表（只能从这里选择）】

{characters}

---

## 【输出格式（必须严格遵守）】

```json
{{
  "shots": [
    {{
      "order_index": 1,
      "shot": "高度具体、可被直接看见的画面描述，包含起始状态到结束状态的连续变化。",
      "dialogue": "角色对话内容（若无对话则为空字符串）",
      "characters": ["角色名1", "角色名2"]
    }}
  ]
}} 
```

---

## 【Shot 写作规范（极其重要）】

`shot` 字段不是摘要，也不是文学概述，而是：

> **一个可被“首帧 + 尾帧”完全锁定的电影画面状态变化描述**

每一个 Shot 的描述应尽量包含（不需要分点）：

* **起始画面状态**：人物姿态、物体位置、构图、光影
* **连续可见动作**：可在 8 秒内自然完成的动作序列
* **结束画面状态**：动作完成后的最终姿态或画面结果
* **构图与景别**：特写 / 中景 / 全景 / 角度
* **光影与色调**：光线方向、对比度、色彩氛围
* **环境与道具**：背景元素、空间关系
* **情绪呈现**：只能通过可见动作与最终状态体现

  * ❌ 禁止心理描写
  * ❌ 禁止抽象情绪总结

---

## 【对话使用原则（严格限制）】

* 一个 8 秒 Shot **最多 1–2 句关键对话**
* 对话必须伴随明确的可见动作或姿态
* **禁止依赖对话完成情绪转折**
* 情绪转折必须体现在 **Shot 结束画面**

---

## 【8 秒分镜拆分原则】

### 镜头数量控制

* 简单场景：2–3 个 Shot（16–24 秒）
* 对话场景：3–5 个 Shot（24–40 秒）
* 动作场景：4–6 个 Shot（32–48 秒）
* **目标：每个场景 3–5 个 Shot，避免碎片化**

### 何时拆分新 Shot（只限以下情况）

* 视角发生重大变化（全景 → 特写）
* 空间发生转换（室内 → 室外）
* 明确时间跳跃
* 关键情绪或叙事落点需要新的“结束画面”

### 避免拆分的情况

* ❌ 单一简单动作
* ❌ 连续动作的人为拆分
* ❌ 为每句对话拆 Shot
* ❌ 小幅角度变化

---

## 【重要提醒】

* Shot 的本质不是“讲故事”，而是 **定义一个 8 秒画面从 A 到 B 的可见变化**
* 所有“转折”“张力”“情绪爆点”，**必须落在 Shot 的尾帧**

---

## 【待拆分场景】

{scene}

---
"""

    @classmethod
    def get_shot_extraction_prompt(cls, characters: str, scene: str) -> str:
        """
        获取分镜提取Prompt
        
        Args:
            characters: JSON格式的角色列表
            scene: 场景描述
            
        Returns:
            str: 格式化后的prompt
        """
        return cls.SHOT_EXTRACTION.format(characters=characters, scene=scene)

    # 场景图生成Prompt
    SCENE_IMAGE_GENERATION = """Create a cinematic establishing shot of the following environment.
This is a LIVE-ACTION PHOTOGRAPH for a film production, not CGI or 3D render.

## Scene Description
{scene_description}

## Prompt Structure (Apply Veo 3.1 Formula)

### [Cinematography]
Choose appropriate camera work for establishing the environment:
- Camera angle: Wide establishing shot, aerial view, crane shot, sweeping panorama, high angle (show scope), eye-level perspective
- Composition: Rule of thirds, leading lines, depth layers (foreground/midground/background), balanced framing
- Lens: Wide-angle lens for expansive views, deep focus to capture environmental detail

### [Environment Subject]
The location and setting itself is the subject:
- Identify the main environmental elements (landscape, architecture, interior space, natural features)
- Emphasize spatial relationships and scale
- Highlight distinctive characteristics of the location

### [Atmospheric Context]
Define the temporal and weather conditions:
- Time of day: Golden hour (warm sunset/sunrise light), blue hour (twilight), midday sun, overcast day, night
- Weather: Clear skies, scattered clouds, fog/mist, light rain, snow, storm clouds gathering
- Season: Spring bloom, summer lushness, autumn colors, winter bareness (if relevant)

### [Style & Ambiance]
Establish the mood and visual aesthetic:
- Lighting quality: Soft diffused natural light, dramatic shadows and highlights, volumetric light rays through atmosphere, ambient environmental glow, harsh direct sunlight
- Mood: Serene and peaceful, ominous and foreboding, mysterious and enigmatic, vibrant and lively, desolate and abandoned, welcoming and warm
- Aesthetic: Cinematic film photography, photorealistic, rich color palette or muted tones, high dynamic range

## Critical Requirements

**UNINHABITED ENVIRONMENT - No Human Presence:**
- This is a pristine, empty, deserted location
- Vacant space with no people, figures, or human activity
- Unpopulated natural landscape or abandoned built environment
- No human silhouettes, shadows, or reflections
- No crowds, groups, individuals, or any human-like shapes
- The environment exists in complete solitude

**Technical Specifications:**
- Shot on professional cinema camera (ARRI Alexa, RED, Sony Venice)
- Cinematic color grading with film look (not digital/video look)
- High dynamic range with rich environmental detail
- Professional landscape or architectural photography standards
- Natural depth of field characteristic of cinema lenses

**Forbidden Elements:**
- NO 3D rendering artifacts or CGI aesthetics
- NO video game or synthetic imagery look
- NO people, characters, humans, persons, faces, bodies
- NO human-made activity or human presence indicators
- NO mannequins or human-shaped objects

Generate a detailed, cinematic establishing shot that captures the essence and atmosphere of this environment."""

    @classmethod
    def get_scene_image_prompt(cls, scene_description: str) -> str:
        """
        获取场景图生成Prompt (基于原始场景描述)
        
        Args:
            scene_description: 场景描述
            
        Returns:
            str: 格式化后的prompt
        """
        return cls.SCENE_IMAGE_GENERATION.format(scene_description=scene_description)
    
    # 基于分镜描述的场景图生成Prompt
    SCENE_IMAGE_FROM_SHOTS = """Create a cinematic establishing shot based on the visual elements described in the following shots.
This is a LIVE-ACTION PHOTOGRAPH for a film production, not CGI or 3D render.

## Shots Description
{shots_description}

## Your Task
Analyze the shots above and extract the COMMON ENVIRONMENTAL ELEMENTS that appear across these shots.
Focus on creating an establishing shot that shows the LOCATION and ATMOSPHERE where these shots take place.

### Extract These Elements:
1. **Location Type**: Indoor/outdoor, specific place (office, street, castle, etc.)
2. **Architectural Details**: Buildings, structures, room layout, furniture placement
3. **Lighting Conditions**: Time of day, light sources, shadows, atmosphere
4. **Weather/Atmosphere**: Clear, rainy, foggy, stormy, etc.
5. **Color Palette**: Dominant colors, tones, mood
6. **Spatial Layout**: How the space is organized, key landmarks

### Generate Establishing Shot Prompt:

Use Veo 3.1 Formula:
- **[Cinematography]**: Wide establishing shot, appropriate angle to show the space
- **[Environment Subject]**: The location itself (NO people, NO characters)
- **[Atmospheric Context]**: Time of day, weather, lighting from the shots
- **[Style & Ambiance]**: Mood and aesthetic matching the shots

## Critical Requirements

**UNINHABITED ENVIRONMENT - No Human Presence:**
- Extract ONLY the environment from the shots, remove ALL human elements
- This is a pristine, empty, deserted location
- NO people, characters, humans, persons, faces, bodies
- NO human silhouettes, shadows, or reflections
- The environment exists in complete solitude

**Match the Shots' Visual Style:**
- Use the same lighting conditions described in the shots
- Match the time of day and weather
- Maintain the same color palette and mood
- Ensure the establishing shot feels like it belongs to the same scene

**Technical Specifications:**
- Shot on professional cinema camera (ARRI Alexa, RED, Sony Venice)
- Cinematic color grading with film look
- High dynamic range with rich environmental detail
- Professional landscape or architectural photography standards

**FORBIDDEN - ABSOLUTELY NO:**
- ❌ 3D rendering or CGI aesthetics
- ❌ Computer-generated imagery of any kind
- ❌ Video game graphics or synthetic visuals
- ❌ Perfect geometric shapes or artificial smoothness
- ❌ Unnatural lighting or impossible light sources
- ❌ Overly saturated or artificial colors
- ❌ Clean, perfect surfaces (real world has imperfections)

Generate a detailed, cinematic establishing shot that captures the environment where these shots take place."""

    @classmethod
    def get_scene_image_prompt_from_shots(cls, shots_description: str) -> str:
        """
        基于分镜描述生成场景图提示词
        
        Args:
            shots_description: 场景的所有分镜描述(组合)
            
        Returns:
            str: 格式化后的prompt
        """
        return cls.SCENE_IMAGE_FROM_SHOTS.format(shots_description=shots_description)

    # 过渡视频提示词生成Prompt
    TRANSITION_VIDEO = """
你是一名**国际获奖级电影视频提示词生成专家**，精通 **Google Veo 3.1** 的视频生成最佳实践。

你的任务是：
**根据给定的两个分镜描述，生成一个用于 AI 视频生成的【中文视频提示词】**，用于在**首帧与尾帧之间生成一个固定 8 秒的连续过渡视频**。

---

### 【模型适配前提（必须遵守）】

* 视频基于 **首帧 + 尾帧** 生成
* 中间画面为模型进行的**连续视觉插值**
* 模型只理解 **画面状态从 A 到 B 的变化**

因此：

* 只允许 **一个连续镜头**
* 禁止剪辑、跳切、叙事跳跃
* 所有关键变化必须在 **尾帧画面状态中成立**

---

### 【输出要求（强制）】

* **只输出中文视频提示词本身**
* 禁止任何解释、标题、标记、注释
* 提示词需自然融合 **Veo 3.1 五部分公式**：

  * **Cinematography**：镜头运动、构图、焦距
  * **Subject**：角色或视觉焦点（与分镜严格一致）
  * **Action**：8 秒内可完成的连续动作
  * **Context**：环境与空间
  * **Style & Ambiance**：光线、情绪、美学

---

### 【摄影语言约束】

* 单一连续镜头（no cuts）
* 允许镜头运动：dolly shot, tracking shot, slow pan, push in, pull back, arc shot
* 明确景别：wide shot, medium shot, close-up, extreme close-up
* 明确焦距：shallow depth of field, deep focus, rack focus

---

### 【音频规则（极其重要）】

* **严格禁止任何背景音乐**
* 禁止 BGM、配乐、旋律、节奏音乐
* 只允许真实声音：

**物理音效**（必须使用前缀）
`SFX: footsteps, fabric rustling, breathing, object handling`

**环境音**（必须使用前缀）
`Ambient noise: room tone, wind, distant traffic`

* 必须明确写出：
  **NO background music, NO BGM, NO soundtrack**

---

### 【角色名称保护】

* 所有角色名称必须与输入 **完全一致**
* 不允许翻译、音译或修改
* 中文名必须原样保留

---

### 【风格要求】

* 强调 **live-action realism**
* cinematic, realistic, filmic
* 情绪通过 **可见动作与最终画面状态**体现，禁止抽象情绪描述

---

### 【生成重点】

* 明确从 **第一个分镜画面状态** 开始
* 通过平滑连续运动
* 自然过渡到 **第二个分镜画面状态**
* 禁止引入新角色、新道具、新场景

---

### 【两个分镜的描述】

{combined_text}

---
"""

    @classmethod
    def get_transition_video_prompt(cls, combined_text: str) -> str:
        """
        获取过渡视频提示词生成Prompt
        
        Args:
            combined_text: 组合的两个分镜描述
            
        Returns:
            str: 格式化后的prompt
        """
        return cls.TRANSITION_VIDEO.format(combined_text=combined_text)


__all__ = ["MoviePromptTemplates"]
