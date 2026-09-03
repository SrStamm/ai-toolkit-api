import express, { type Express } from "express";
import agentRouter from "./routes/agent.router";

const app: Express = express();

app.use(express.json());

app.use("/agent", agentRouter);

export default app;
