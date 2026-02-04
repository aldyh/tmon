"""
PlatformIO extra script to set SLAVE_ADDR from environment variable.
"""
Import("env")
import os

slave_addr = os.environ.get("SLAVE_ADDR")
if slave_addr is not None:
    env.Append(BUILD_FLAGS=[f"-DSLAVE_ADDR={slave_addr}"])
