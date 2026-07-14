import asyncio
import sys

async def main():
    try:
        print("Spawning directApplyExecutor...")
        p = await asyncio.create_subprocess_exec(
            'node',
            '../directApplyExecutor.js',
            'https://example.com',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        while True:
            line = await p.stdout.readline()
            if not line:
                break
            print("SUB:", line.decode().strip())
            sys.stdout.flush() # Force flush Python's stdout
        await p.wait()
        print("Exit code:", p.returncode)
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    asyncio.run(main())
