import argparse
import socket

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Run the main local RAG API.")
    parser.add_argument("--port", type=int, default=8001)
    arguments = parser.parse_args()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", arguments.port))
    listener.listen(128)
    print("BACKEND_PORT=" + str(listener.getsockname()[1]), flush=True)
    configuration = uvicorn.Config("app.main:app", log_level="warning", access_log=False)
    server = uvicorn.Server(configuration)
    try:
        server.run(sockets=[listener])
    finally:
        listener.close()


if __name__ == "__main__":
    main()
