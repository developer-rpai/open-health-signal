import { serviceClient } from "../_shared/db.js";
import { handlePageView } from "../_shared/pageview.js";
import { takeRate } from "../_shared/rate.js";

Deno.serve((req) => handlePageView(req, { serviceClient, takeRate }));
