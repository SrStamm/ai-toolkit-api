import express, { type Express } from "express";
import agentRouter from "./routes/agent.router";
import cors from "cors";

const app: Express = express();

app.use(cors());
app.use(express.json());

app.use("/agent", agentRouter);

export default app;
