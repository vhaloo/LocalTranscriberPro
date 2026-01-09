import base64
import os

# Paths
base_dir = r"C:\Users\Vhaloo\Desktop\LocalTranscriber"
app_file = os.path.join(base_dir, "local_transcriber.py")
template_file = os.path.join(base_dir, "installer_template.py")
output_file = os.path.join(base_dir, "installer.py")

print("Reading app source...")
with open(app_file, "rb") as f:
    app_source = f.read()

print("Encoding to Base64...")
app_b64 = base64.b64encode(app_source).decode("utf-8")

print("Reading template...")
with open(template_file, "r", encoding="utf-8") as f:
    template = f.read()

print("Replacing placeholder...")
final_code = template.replace("__APP_BASE64__", app_b64)

print("Writing installer.py...")
with open(output_file, "w", encoding="utf-8") as f:
    f.write(final_code)

print("Done.")
