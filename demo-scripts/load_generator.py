#!/usr/bin/env python3
"""
System Load Generator for Demo
Generates CPU, memory, and disk load for demonstration purposes
"""
import time
import threading
import os
import random
import sys
from multiprocessing import Process, cpu_count

def cpu_load(duration=60):
    """Generate CPU load"""
    print(f"🔥 Starting CPU load for {duration} seconds...")
    end_time = time.time() + duration
    while time.time() < end_time:
        # Busy wait to consume CPU
        for _ in range(1000000):
            pass

def memory_load(size_mb=100, duration=60):
    """Generate memory load"""
    print(f"🧠 Starting memory load ({size_mb}MB) for {duration} seconds...")
    data = []
    end_time = time.time() + duration
    while time.time() < end_time:
        # Allocate memory in chunks
        chunk = 'x' * (1024 * 1024)  # 1MB chunk
        data.append(chunk)
        if len(data) > size_mb:
            data.pop(0)
        time.sleep(0.1)

def disk_load(duration=60):
    """Generate disk I/O load"""
    print(f"💾 Starting disk I/O load for {duration} seconds...")
    end_time = time.time() + duration
    file_counter = 0
    while time.time() < end_time:
        try:
            # Write and read files
            filename = f'/tmp/demo_load_file_{file_counter}'
            with open(filename, 'w') as f:
                f.write('x' * 1024 * 1024)  # 1MB
            with open(filename, 'r') as f:
                f.read()
            os.remove(filename)
            file_counter += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"Disk load error: {e}")
            time.sleep(1)

def network_load(duration=60):
    """Generate network load by making HTTP requests"""
    print(f"🌐 Starting network load for {duration} seconds...")
    import urllib.request
    end_time = time.time() + duration
    while time.time() < end_time:
        try:
            # Make requests to generate network traffic
            urllib.request.urlopen('http://httpbin.org/get', timeout=5)
            time.sleep(1)
        except Exception as e:
            print(f"Network load error: {e}")
            time.sleep(2)

def print_system_info():
    """Print current system information"""
    print("\n📊 Current System Information:")
    print("=" * 40)
    
    try:
        import psutil
        print(f"CPU Usage: {psutil.cpu_percent(interval=1):.1f}%")
        print(f"Memory Usage: {psutil.virtual_memory().percent:.1f}%")
        print(f"Disk Usage: {psutil.disk_usage('/').percent:.1f}%")
        print(f"CPU Cores: {psutil.cpu_count()}")
        print(f"Total Memory: {psutil.virtual_memory().total / (1024**3):.1f} GB")
    except ImportError:
        print("psutil not available - install with: pip install psutil")
    
    print("=" * 40)

def main():
    """Main function to orchestrate load generation"""
    print("🚀 System Load Generator for Demo")
    print("=" * 50)
    
    # Parse command line arguments
    duration = 120  # Default 2 minutes
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print("Invalid duration. Using default 120 seconds.")
    
    print(f"⏱️  Load generation duration: {duration} seconds")
    
    # Show initial system state
    print_system_info()
    
    print("\n🔥 Starting load generation...")
    print("📈 Monitor your dashboard to see metrics change!")
    
    # Start different types of load
    processes = []
    threads = []
    
    # CPU load on multiple cores (but not all to keep system responsive)
    cpu_cores_to_use = min(4, max(1, cpu_count() - 1))
    print(f"🔥 Starting CPU load on {cpu_cores_to_use} cores...")
    for i in range(cpu_cores_to_use):
        p = Process(target=cpu_load, args=(duration,))
        p.start()
        processes.append(p)
    
    # Memory load
    memory_thread = threading.Thread(target=memory_load, args=(200, duration))
    memory_thread.start()
    threads.append(memory_thread)
    
    # Disk load
    disk_thread = threading.Thread(target=disk_load, args=(duration,))
    disk_thread.start()
    threads.append(disk_thread)
    
    # Network load (optional)
    try:
        network_thread = threading.Thread(target=network_load, args=(duration,))
        network_thread.start()
        threads.append(network_thread)
    except Exception as e:
        print(f"⚠️  Network load disabled: {e}")
    
    # Progress indicator
    start_time = time.time()
    while time.time() - start_time < duration:
        elapsed = time.time() - start_time
        remaining = duration - elapsed
        progress = (elapsed / duration) * 100
        
        print(f"\r⏳ Progress: {progress:.1f}% | Remaining: {remaining:.0f}s", end="", flush=True)
        time.sleep(5)
    
    print("\n\n⏹️  Stopping load generation...")
    
    # Wait for all processes and threads to complete
    for p in processes:
        p.join(timeout=10)
        if p.is_alive():
            p.terminate()
    
    for t in threads:
        t.join(timeout=10)
    
    print("✅ Load generation completed!")
    
    # Show final system state
    time.sleep(2)  # Wait a moment for metrics to settle
    print_system_info()
    
    print("\n🎉 Demo load generation finished!")
    print("📊 Check your Grafana dashboard to see the impact!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Load generation interrupted by user")
        print("🛑 Cleaning up...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error during load generation: {e}")
        sys.exit(1)
