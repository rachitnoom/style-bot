import { Router, type IRouter } from "express";
import healthRouter from "./health";
import presenceRouter from "./presence";
import uptimeRouter from "./uptime";

const router: IRouter = Router();

router.use(healthRouter);
router.use(presenceRouter);
router.use(uptimeRouter);

export default router;
