import express from "express";
import { streamAgentLoop, listProviders } from "./agent.controller";

const agentRouter = express.Router();

agentRouter.post("/agent-loop/stream", streamAgentLoop);
agentRouter.get("/providers", listProviders);

export default agentRouter;
