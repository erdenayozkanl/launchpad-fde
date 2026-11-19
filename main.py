import argparse, uvicorn
parser = argparse.ArgumentParser(description="Launchpad FDE deployment accelerator")
parser.add_argument("--serve", action="store_true")
if parser.parse_args().serve: uvicorn.run("api:app", host="127.0.0.1", port=8005)
else: parser.print_help()
