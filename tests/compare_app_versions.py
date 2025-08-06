#!/usr/bin/env python3
"""
Compare app.py versions between local and Docker
Helps identify if the Docker image has the scenario detection fix
"""

import difflib
import os
import re

def extract_relevant_section(content, start_line=320, end_line=350):
    """Extract the relevant section around the scenario detection"""
    lines = content.split('\n')
    return '\n'.join(lines[start_line-1:end_line])

def check_for_fix(content):
    """Check if the scenario detection fix is present"""
    indicators = [
        "# Recalculate for scenario detection",
        "has_effects = bool(data.get('effects', []))",
        "has_subtitles = bool(data.get('subtitle'))"
    ]
    
    # Check if all indicators are present near line 328-330
    lines = content.split('\n')
    for i in range(320, min(340, len(lines))):
        if i < len(lines) and "# Recalculate for scenario detection" in lines[i]:
            # Check if the next lines have the recalculation
            if (i+1 < len(lines) and "has_effects = bool(data.get('effects', []))" in lines[i+1] and
                i+2 < len(lines) and "has_subtitles = bool(data.get('subtitle'))" in lines[i+2]):
                return True, i+1
    
    return False, None

def compare_files(local_path, docker_path):
    """Compare local and Docker app.py files"""
    
    print("App.py Version Comparison")
    print("========================")
    
    # Read local version
    with open(local_path, 'r') as f:
        local_content = f.read()
    
    # Read Docker version (if exists)
    docker_content = ""
    if os.path.exists(docker_path):
        with open(docker_path, 'r') as f:
            docker_content = f.read()
    else:
        print(f"\n⚠️  Docker app.py not found at: {docker_path}")
        print("Run the test first to extract it from the Docker image.")
        return
    
    # Check for fix in both versions
    print("\n1. Checking for scenario detection fix...")
    
    local_has_fix, local_line = check_for_fix(local_content)
    docker_has_fix, docker_line = check_for_fix(docker_content)
    
    print(f"\nLocal app.py:")
    if local_has_fix:
        print(f"  ✓ Has fix at line {local_line}")
    else:
        print("  ✗ Missing fix")
    
    print(f"\nDocker app.py:")
    if docker_has_fix:
        print(f"  ✓ Has fix at line {docker_line}")
    else:
        print("  ✗ Missing fix")
    
    # Show the relevant section from both files
    print("\n2. Scenario detection section comparison:")
    print("\n--- Local app.py (lines 320-350) ---")
    print(extract_relevant_section(local_content, 320, 350))
    
    print("\n--- Docker app.py (lines 320-350) ---")
    print(extract_relevant_section(docker_content, 320, 350))
    
    # If files are different, show a unified diff
    if local_content != docker_content:
        print("\n3. Differences found between files:")
        
        # Create a unified diff
        local_lines = local_content.splitlines(keepends=True)
        docker_lines = docker_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            docker_lines,
            local_lines,
            fromfile='docker/app.py',
            tofile='local/app.py',
            n=3
        )
        
        # Filter to show only relevant differences
        print("\nRelevant differences (around scenario detection):")
        in_relevant_section = False
        for line in diff:
            if any(keyword in line for keyword in ['scenario', 'has_effects', 'has_subtitles', '@@']):
                in_relevant_section = True
            
            if in_relevant_section:
                print(line, end='')
                
            if in_relevant_section and line.startswith('@@'):
                # Check if we've moved past the relevant section
                match = re.match(r'@@ -(\d+)', line)
                if match and int(match.group(1)) > 350:
                    break
    else:
        print("\n✓ Files are identical!")
    
    # Summary
    print("\n4. Summary:")
    if not docker_has_fix and local_has_fix:
        print("⚠️  Docker image needs to be rebuilt with the fixed app.py!")
        print("   Run: python3 rebuild_and_push_docker.py")
    elif docker_has_fix and local_has_fix:
        print("✅ Both versions have the fix. Docker image should work correctly.")
    elif not docker_has_fix and not local_has_fix:
        print("❌ Neither version has the fix! This is unexpected.")
    else:
        print("🤔 Unexpected state - please investigate manually.")


def main():
    """Main function"""
    # Paths
    local_app = "/Users/lgg/coding/sumatman/runpod/video_generation/app.py"
    docker_app = "/Users/lgg/coding/sumatman/runpod/Temps/docker_app.py"
    
    compare_files(local_app, docker_app)
    
    print("\n" + "="*50)
    print("Next steps:")
    print("1. If Docker image needs rebuild: python3 rebuild_and_push_docker.py")
    print("2. To test Docker image: python3 test_docker_full_featured.py")


if __name__ == "__main__":
    main()