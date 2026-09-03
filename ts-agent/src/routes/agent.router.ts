import express from "express";
import { streamAgentLoop } from "./agent.controller";

const agentRouter = express.Router();

agentRouter.post("/agent-loop/stream", streamAgentLoop);

export default agentRouter;
