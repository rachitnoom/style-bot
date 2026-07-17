import { Router, type IRouter } from "express";
import healthRouter from "./health";
import presenceRouter from "./presence";

const router: IRouter = Router();

router.use(healthRouter);
router.use(presenceRouter);

export default router;
