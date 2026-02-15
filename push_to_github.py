#!/usr/bin/env python3
"""
Push project to GitHub using subprocess
"""
import subprocess
import os
import sys

os.chdir(r'd:\WRKSPC\agentic_auto_routing')

GIT_PATH = r'C:\Program Files\Git\bin\git.exe'

commands = [
    # Configure git
    [GIT_PATH, 'config', 'user.email', 'rudra@example.com'],
    [GIT_PATH, 'config', 'user.name', 'Rudra-J'],
    
    # Check status
    [GIT_PATH, 'status'],
    
    # Add all files (except .env - it's in .gitignore)
    [GIT_PATH, 'add', '.'],
    
    # Verify .env is excluded
    [GIT_PATH, 'status'],
    
    # Commit
    [GIT_PATH, 'commit', '-m', 'Initial commit: Agentic Multi-Modal Route Optimizer\n\n- Intelligent transportation planning with NLP\n- Graph-based multi-modal route optimization\n- Leg-specific constraint handling\n- Comprehensive test suite\n- Full-stack implementation (FastAPI + Vanilla JS)'],
    
    # Add remote
    [GIT_PATH, 'remote', 'add', 'origin', 'https://github.com/Rudra-J/Agentic-Multi-modal-Route-Optimizer.git'],
    
    # Verify remote
    [GIT_PATH, 'remote', '-v'],
    
    # Set main branch
    [GIT_PATH, 'branch', '-M', 'main'],
    
    # Push to GitHub
    [GIT_PATH, 'push', '-u', 'origin', 'main'],
    
    # Verify push
    [GIT_PATH, 'log', '--oneline'],
]

print("=" * 70)
print("PUSHING TO GITHUB")
print("=" * 70)

for i, cmd in enumerate(commands, 1):
    print(f"\n[Step {i}] Running: {' '.join(cmd)}")
    print("-" * 70)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=r'd:\WRKSPC\agentic_auto_routing')
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode != 0 and 'fatal: remote origin already exists' not in result.stderr:
            print(f"❌ Command failed with return code {result.returncode}")
            # Continue anyway for some commands
        else:
            print(f"✓ Step {i} completed")
            
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "=" * 70)
print("PUSH COMPLETE!")
print("=" * 70)
print("\nVerify at: https://github.com/Rudra-J/Agentic-Multi-modal-Route-Optimizer")
