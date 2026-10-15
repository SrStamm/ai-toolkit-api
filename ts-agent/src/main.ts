import app from "./app";
import { logger } from "./lib/logger";

const log = logger.child("main");

const port = process.env.PORT;

app.listen(port, () => {
  log.info("server_started", {
    port,
    node_env: process.env.NODE_ENV || "development",
  });
});
