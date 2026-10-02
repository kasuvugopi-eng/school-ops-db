import os
import re

models_dir = "backend/app/models"
app_dir = "backend/app"

def fix_models():
    changed_files = []
    for root, _, files in os.walk(models_dir):
        for file in files:
            if not file.endswith(".py"): continue
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            new_content = re.sub(r"mapped_column\(\s*DateTime\s*(,|\))", r"mapped_column(DateTime(timezone=True)\1", content)
            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                changed_files.append(filepath)
    return changed_files

def fix_app():
    changed_files = []
    for root, _, files in os.walk(app_dir):
        if "models" in root: continue
        if "alembic" in root: continue # wait, alembic is usually in backend/alembic or backend/migrations, but just to be sure.
        for file in files:
            if not file.endswith(".py"): continue
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            new_content = content
            # datetime.utcnow() -> datetime.now(timezone.utc)
            new_content = new_content.replace("datetime.utcnow()", "datetime.now(timezone.utc)")
            # datetime.now() -> datetime.now(timezone.utc)
            new_content = re.sub(r"datetime\.now\(\)", "datetime.now(timezone.utc)", new_content)
            
            # remove .replace(tzinfo=None)
            new_content = new_content.replace(".replace(tzinfo=None)", "")

            if new_content != content:
                # Add `from datetime import timezone` if timezone.utc is used but timezone is not imported
                # Let's use a regex to check if timezone is imported from datetime
                if "timezone" not in content and "timezone.utc" in new_content:
                    if re.search(r"from\s+datetime\s+import\s+[^(\n]*datetime", new_content):
                        new_content = re.sub(r"(from\s+datetime\s+import\s+.*?datetime[^\n]*)", r"\1, timezone", new_content)
                    else:
                        new_content = "from datetime import timezone\n" + new_content
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                changed_files.append(filepath)
    return changed_files

if __name__ == "__main__":
    mf = fix_models()
    af = fix_app()
    print("Models fixed:", mf)
    print("App fixed:", af)
