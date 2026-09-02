#!/usr/bin/env python3
"""
Skills 目錄生成器
生成完整的 skills 分類目錄
"""

import os
import json
from pathlib import Path

# Skills 目錄
HERMES_SKILLS = Path.home() / ".hermes/skills"
AGENTS_SKILLS = Path.home() / ".agents/skills"
OPENCODE_SKILLS = Path.home() / ".config/opencode/skills"

# 分類定義
CATEGORIES = {
    "addyosmani": {
        "name": "Addy Osmani 系列",
        "description": "前端工程化、代碼審查、安全、效能優化等最佳實踐",
        "skills": []
    },
    "ai-agent": {
        "name": "AI Agent",
        "description": "多 Agent 協調、Agent 架構設計、LangChain/LangGraph",
        "skills": []
    },
    "creative": {
        "name": "創意設計",
        "description": "視覺設計、動畫、影像生成、PPT、資訊圖",
        "skills": []
    },
    "hyperframes": {
        "name": "HyperFrames",
        "description": "動畫視頻製作框架",
        "skills": []
    },
    "devops": {
        "name": "DevOps",
        "description": "CI/CD、Kubernetes、Terraform、雲平台",
        "skills": []
    },
    "security": {
        "name": "安全審計",
        "description": "安全掃描、滲透測試、漏洞修復",
        "skills": []
    },
    "data-science": {
        "name": "數據科學",
        "description": "數據分析、MLops、向量資料庫",
        "skills": []
    },
    "productivity": {
        "name": "生產力工具",
        "description": "Notion、Airtable、Google Workspace、文檔處理",
        "skills": []
    },
    "media": {
        "name": "媒體處理",
        "description": "YouTube、GIF、音訊、影片處理",
        "skills": []
    },
    "research": {
        "name": "研究與知識",
        "description": "學術研究、論文檢索、知識庫管理",
        "skills": []
    },
    "social-media": {
        "name": "社群媒體",
        "description": "X/Twitter、WeChat、微博、FB Marketplace",
        "skills": []
    },
    "taiwan": {
        "name": "台灣本地化",
        "description": "台灣網站搜尋、拍賣、求職",
        "skills": []
    },
    "video": {
        "name": "影片製作",
        "description": "影片轉錄、字幕生成、剪輯",
        "skills": []
    },
    "other": {
        "name": "其他",
        "description": "未分類技能",
        "skills": []
    }
}

def find_skill_md(skill_path):
    """查找 SKILL.md 文件"""
    skill_md = skill_path / "SKILL.md"
    if skill_md.exists():
        return skill_md.read_text(encoding='utf-8', errors='ignore')
    return None

def extract_skill_info(content):
    """從 SKILL.md 提取元數據"""
    if not content:
        return {}
    
    info = {}
    for line in content.split('\n')[:50]:
        if line.startswith('---'):
            continue
        if line.startswith('name:'):
            info['name'] = line.split(':', 1)[1].strip().strip('"')
        elif line.startswith('description:'):
            info['description'] = line.split(':', 1)[1].strip().strip('"')
        elif line.startswith('version:'):
            info['version'] = line.split(':', 1)[1].strip().strip('"')
        elif line.startswith('triggers:'):
            # 讀取下一行作為觸發詞
            pass
    return info

def categorize_skill(skill_name, info):
    """對技能進行分類"""
    name_lower = skill_name.lower()
    desc_lower = (info.get('description', '') or '').lower()
    combined = f"{name_lower} {desc_lower}"
    
    if 'addyosmani' in name_lower or 'code-review' in name_lower or 'security' in name_lower or 'performance' in name_lower:
        return 'addyosmani'
    elif 'agent' in name_lower or 'langchain' in name_lower or 'crewai' in name_lower:
        return 'ai-agent'
    elif 'design' in name_lower or 'animation' in name_lower or 'video' in name_lower or 'image' in name_lower or 'creative' in name_lower or 'illustrat' in name_lower:
        return 'creative'
    elif 'hyperframes' in name_lower:
        return 'hyperframes'
    elif 'kubernetes' in name_lower or 'terraform' in name_lower or 'ci-cd' in name_lower or 'docker' in name_lower:
        return 'devops'
    elif 'security' in name_lower or 'vulnerability' in name_lower or 'penetration' in name_lower or 'sast' in name_lower or 'dast' in name_lower:
        return 'security'
    elif 'data' in name_lower or 'ml' in name_lower or 'mlops' in name_lower or 'vector' in name_lower or 'llm' in name_lower:
        return 'data-science'
    elif 'notion' in name_lower or 'airtable' in name_lower or 'google' in name_lower or 'pdf' in name_lower or 'doc' in name_lower:
        return 'productivity'
    elif 'youtube' in name_lower or 'gif' in name_lower or 'audio' in name_lower or 'music' in name_lower or 'spotify' in name_lower:
        return 'media'
    elif 'research' in name_lower or 'arxiv' in name_lower or 'wiki' in name_lower or 'literature' in name_lower:
        return 'research'
    elif 'twitter' in name_lower or 'weibo' in name_lower or 'wechat' in name_lower or 'facebook' in name_lower or 'xurl' in name_lower:
        return 'social-media'
    elif 'taiwan' in name_lower or '104' in name_lower or 'job' in name_lower or 'marketplace' in name_lower:
        return 'taiwan'
    elif 'transcript' in name_lower or 'subtitle' in name_lower or 'whisper' in name_lower or 'video' in name_lower:
        return 'video'
    else:
        return 'other'

def scan_skills(skill_dir):
    """掃描技能目錄"""
    skills = []
    if not skill_dir.exists():
        return skills
    
    for item in sorted(skill_dir.iterdir()):
        if item.is_dir() and not item.name.startswith('.'):
            skill_name = item.name
            skill_md = item / "SKILL.md"
            content = find_skill_md(item)
            info = extract_skill_info(content)
            category = categorize_skill(skill_name, info)
            
            skills.append({
                'name': skill_name,
                'path': str(item),
                'info': info,
                'category': category,
                'has_skill_md': skill_md.exists()
            })
    
    return skills

def generate_catalog():
    """生成完整的目錄"""
    all_skills = []
    
    # 掃描三個目錄
    for skill_dir in [HERMES_SKILLS, AGENTS_SKILLS, OPENCODE_SKILLS]:
        all_skills.extend(scan_skills(skill_dir))
    
    # 去重
    unique_skills = {}
    for skill in all_skills:
        key = skill['name']
        if key not in unique_skills:
            unique_skills[key] = skill
        else:
            # 保留有更多資訊的版本
            if skill.get('has_skill_md') and not unique_skills[key].get('has_skill_md'):
                unique_skills[key] = skill
    
    # 按分類組織
    categorized = {cat: [] for cat in CATEGORIES}
    for skill in unique_skills.values():
        cat = skill['category']
        if cat in categorized:
            categorized[cat].append(skill)
    
    return categorized, len(unique_skills)

def write_report(categorized, total_count):
    """寫入報告文件"""
    output_path = Path.home() / "Desktop" / "skills-catalog-full.md"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# AI Agent Skills 完整目錄\n\n")
        f.write(f"> 生成時間: {Path.home()}/Desktop/skills-catalog-full.md\n")
        f.write(f"> 總技能數: {total_count} 個\n\n")
        
        f.write("## 目錄結構\n\n")
        f.write("| 分類 | 數量 | 說明 |\n")
        f.write("|------|------|------|\n")
        
        for cat_name, cat_data in CATEGORIES.items():
            count = len(categorized.get(cat_name, []))
            f.write(f"| {cat_data['name']} | {count} | {cat_data['description']} |\n")
        
        f.write("\n---\n\n")
        
        for cat_name, cat_data in CATEGORIES.items():
            skills = categorized.get(cat_name, [])
            if not skills:
                continue
            
            f.write(f"## {cat_data['name']}\n\n")
            f.write(f"**說明:** {cat_data['description']}\n\n")
            f.write("| 名稱 | 路徑 | 說明 |\n")
            f.write("|------|------|------|\n")
            
            for skill in skills:
                name = skill['name']
                path = skill['path'].replace(str(Path.home()), '~')
                desc = skill.get('info', {}).get('description', '無描述')
                # 截斷描述
                if len(desc) > 60:
                    desc = desc[:57] + "..."
                f.write(f"| {name} | `{path}` | {desc} |\n")
            
            f.write("\n")
        
        f.write("---\n\n")
        f.write("## 使用說明\n\n")
        f.write("### 安裝位置\n\n")
        f.write("- **Hermes:** `~/.hermes/skills/`\n")
        f.write("- **Agents:** `~/.agents/skills/`\n")
        f.write("- **OpenCode:** `~/.config/opencode/skills/`\n\n")
        
        f.write("### 載入方式\n\n")
        f.write("```bash\n")
        f.write("# Hermes\n")
        f.write("hermes skills list\n\n")
        f.write("# OpenCode\n")
        f.write("opencode skills list\n\n")
        f.write("# 手動載入\n")
        f.write("skill_view(name='skill-name')\n")
        f.write("```\n\n")
        
        f.write("### 遷移腳本\n\n")
        f.write("使用 `skill-manager.sh` 同步 skills 到不同 agent:\n\n")
        f.write("```bash\n")
        f.write("cd ~/.agents/skills\n")
        f.write("./skill-manager.sh sync\n")
        f.write("```\n\n")
    
    print(f"Report written to: {output_path}")
    return output_path

if __name__ == '__main__':
    categorized, total = generate_catalog()
    output = write_report(categorized, total)
    print(f"Total skills cataloged: {total}")
    print(f"Output: {output}")
