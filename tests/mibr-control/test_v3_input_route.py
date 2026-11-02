"""Host-compiled actual MIBR/3 ACTION against mock observed owner. NO Unit action."""
from test_native_v3_readonly import NativeV3ReadOnly, api, BIN
import unittest
import os
@unittest.skipUnless(BIN,"requires compiled native C host harness")
class RouteInputHost(NativeV3ReadOnly):
    def setUp(self):
        super().setUp()
        self.env["MIBR_V3_HOST_ROUTE_TEST"]="1"
    def fields(self,rid,origin="HMI",target="DIRECT111",route="STOCK110",
               session="7",generation="9"):
        return {"kind":"SET_VISIBLE_ROUTE","target":target,"expected_route":route,
                "expected_session":session,"expected_generation":generation,
                "origin":origin,"request_id":rid}
    def test_exact_key40_input_to_same_native_action_handler(self):
        self.env["MIBR_V3_HOST_INPUT_TEST"]="1"
        p=self.start("input")
        self.assertEqual(self.host_command(p,b"#HOST_KEY40 1\n"),b"HOST_KEY40_NONE\n")
        self.assertEqual(self.host_command(p,b"#HOST_KEY40 3\n"),b"HOST_KEY40_NONE\n")
        action=self.host_command(p,b"#HOST_KEY40 4\n")
        self.assertEqual(api.parse(action,is_response=True)["fields"]["apply"],"ACTIVE")
        self.assertEqual(self.host_command(p,b"#HOST_KEY40 4\n"),b"HOST_KEY40_NONE\n")
        self.assertEqual(self.host_command(p,b"#HOST_KEY40 5\n"),b"HOST_KEY40_NONE\n")
        self.assertEqual(self.host_command(p,b"#HOST_KEY40 0\n"),b"HOST_KEY40_NONE\n")
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_CALLS\n"),b"HOST_ROUTE_CALLS=1\n")
        self.assertEqual(self.ask(p,"route","STATUS")["fields"]["visible_route"],"DIRECT111")
        self.assertEqual(self.host_command(p,b"#HOST_KEY40 1\n"),b"HOST_KEY40_NONE\n")
        self.assertEqual(self.host_command(p,b"#HOST_KEY40 0\n"),b"HOST_KEY40_OEM_SHORT\n")
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_CALLS\n"),b"HOST_ROUTE_CALLS=1\n")
        for x in (1,3):
            self.assertEqual(self.host_command(p,("#HOST_KEY40 %d\n"%x).encode()),b"HOST_KEY40_NONE\n")
        opposite=api.parse(self.host_command(p,b"#HOST_KEY40 4\n"),is_response=True)
        self.assertEqual(opposite["fields"]["target"],"STOCK110")
        self.assertEqual(opposite["fields"]["apply"],"ACTIVE")
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_CALLS\n"),b"HOST_ROUTE_CALLS=2\n")
    def test_no_input_qualifier_never_emits_action(self):
        p=self.start("input")
        for x in (1,3,4,5,0):
            self.assertEqual(self.host_command(p,("#HOST_KEY40 %d\n"%x).encode()),b"HOST_KEY40_UNQUALIFIED\n")
    def test_capability_status_and_exact_apply(self):
        p=self.start("ui")
        self.assertEqual(self.ask(p,"cap","CAPABILITIES")["fields"]["route_action"],"1")
        a=self.ask(p,"s","STATUS")["fields"]
        self.assertEqual((a["route_correlated"],a["visible_route"],a["route_session"],a["route_generation"]),("1","STOCK110","7","9"))
        r=self.ask(p,"go","ACTION",self.fields("go"))
        self.assertIsNone(r["error"],r)
        self.assertEqual((r["fields"]["apply"],r["fields"]["visible_route"],r["fields"]["stored"]),("ACTIVE","DIRECT111","UNCHANGED"))
        self.assertEqual(self.ask(p,"go","ACTION",self.fields("go")),r)
        verified=self.ask(p,"look","ACTION_STATUS",{"request_id":"go"})["fields"]
        self.assertEqual((verified["apply"],verified["receipt_scope"],verified["target"]),
                         ("ACTIVE","HISTORICAL","DIRECT111"))
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_CALLS\n"),b"HOST_ROUTE_CALLS=1\n")
        self.assertEqual(self.ask(p,"stale","ACTION",self.fields("stale"))["error"],"SESSION_STALE")
        self.assertEqual(self.ask(p,"go","ACTION",self.fields("go",target="STOCK110"))["error"],"IDEMPOTENCY_COLLISION")
        now=self.ask(p,"status","STATUS")["fields"]
        self.assertEqual(now["visible_route"],"DIRECT111")
        self.assertEqual(now["route_generation"],"10")
        back=self.ask(p,"back","ACTION",self.fields("back",target="STOCK110",route="DIRECT111",generation="10"))
        self.assertEqual(back["fields"]["apply"],"ACTIVE")
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_CALLS\n"),b"HOST_ROUTE_CALLS=2\n")
    def test_role_separation_and_bounded_field_validation(self):
        ui=self.start("ui"); inp=self.start("input");shell=self.start("shell")
        self.assertEqual(self.ask(ui,"u","ACTION",self.fields("u",origin="KEY40_LONG"))["error"],"FORBIDDEN")
        self.assertEqual(self.ask(inp,"x","ACTION",self.fields("x",origin="HMI"))["error"],"FORBIDDEN")
        self.assertEqual(self.ask(shell,"h","ACTION",self.fields("h"))["error"],"FORBIDDEN")
        self.assertEqual(self.ask(ui,"bad","ACTION",{**self.fields("bad"),"unknown":"1"})["error"],"INVALID_REQUEST")
        self.assertEqual(self.ask(ui,"bad2","ACTION",{**self.fields("bad2"),"expected_generation":"0"})["error"],"INVALID_REQUEST")
        self.assertEqual(self.ask(ui,"bad3","ACTION",{**self.fields("bad3"),"expected_route":"UNKNOWN"})["error"],"INVALID_REQUEST")
        for verb,args in (("GET",{"key":"maxFPS"}),("SNAPSHOT",{"scope":"ui"}),
                          ("SET",{"key":"maxFPS"}),("REQUEST_STATUS",{"request_id":"x"}),
                          ("TEST_LIST",{}),("ACTIVATE",{})):
            self.assertEqual(self.ask(inp,"deny"+verb,verb,args)["error"],"FORBIDDEN")
        r=self.ask(inp,"k4","ACTION",self.fields("k4",origin="KEY40_LONG"))
        self.assertEqual(r["fields"]["apply"],"ACTIVE")
        self.assertEqual(self.ask(ui,"foreign","ACTION_STATUS",{"request_id":"k4"})["error"],"UNKNOWN_COMMIT")  # isolated host processes; actual shared socket tests role denial
        self.assertEqual(self.ask(inp,"its","ACTION_STATUS",{"request_id":"k4"})["fields"]["apply"],"ACTIVE")
        self.assertEqual(self.ask(inp,"badlookup","ACTION_STATUS",{"key":"maxFPS"})["error"],"INVALID_REQUEST")
        self.assertEqual(self.ask(shell,"no","ACTION_STATUS",{"request_id":"absent"})["error"],"FORBIDDEN")
    def test_matching_visible_route_without_matching_request_ack_is_not_active(self):
        self.env["MIBR_V3_HOST_ROUTE_NO_ACK"]="1"
        p=self.start("ui")
        result=self.ask(p,"noack","ACTION",self.fields("noack"))
        self.assertEqual(result["fields"]["apply"],"PENDING")
        self.assertEqual(result["fields"]["visible_route"],"UNKNOWN")
        self.assertEqual(self.ask(p,"state","STATUS")["fields"]["visible_route"],"DIRECT111")
    def test_callback_presence_without_independent_qualification_fails_closed(self):
        self.env["MIBR_V3_HOST_ROUTE_UNQUALIFIED"]="1"
        self.env["MIBR_V3_HOST_INPUT_TEST"]="1"
        p=self.start("input")
        self.assertEqual(self.ask(p,"cap","CAPABILITIES")["fields"]["route_action"],"0")
        self.assertEqual(self.ask(p,"stat","STATUS")["fields"]["route_correlated"],"0")
        self.assertEqual(self.ask(p,"direct","ACTION",self.fields("direct",origin="KEY40_LONG"))["error"],
                         "ACTIVATION_UNSUPPORTED")
        for x in (1,3):self.assertEqual(self.host_command(p,("#HOST_KEY40 %d\n"%x).encode()),b"HOST_KEY40_NONE\n")
        self.assertEqual(self.host_command(p,b"#HOST_KEY40 4\n"),b"HOST_KEY40_UNQUALIFIED\n")
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_CALLS\n"),b"HOST_ROUTE_CALLS=0\n")
    def test_no_adapter_means_no_capability(self):
        self.env.pop("MIBR_V3_HOST_ROUTE_TEST")
        p=self.start("ui")
        self.assertEqual(self.ask(p,"cap","CAPABILITIES")["fields"]["route_action"],"0")
        self.assertEqual(self.ask(p,"status","STATUS")["fields"]["visible_route"],"UNKNOWN")
        self.assertEqual(self.ask(p,"go","ACTION",self.fields("go"))["error"],"ACTIVATION_UNSUPPORTED")
    def test_pending_owner_rejects_second_rid_until_original_ack(self):
        self.env["MIBR_V3_HOST_ROUTE_PENDING"]="1"
        p=self.start("ui")
        first=self.ask(p,"first","ACTION",self.fields("first"))
        self.assertEqual(first["fields"]["apply"],"PENDING")
        self.assertEqual(self.ask(p,"cap0","CAPABILITIES")["fields"]["route_action"],"0")
        self.assertEqual(self.ask(p,"second","ACTION",self.fields("second"))["error"],"NOT_READY")
        self.assertEqual(self.ask(p,"first","ACTION",self.fields("first")),first)
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_CALLS\n"),b"HOST_ROUTE_CALLS=1\n")
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_COMPLETE first\n"),b"HOST_ROUTE_COMPLETE_OK\n")
        # The original historical ACK frees exactly one owner transition slot.
        self.assertEqual(self.ask(p,"confirmed","ACTION_STATUS",{"request_id":"first"})["fields"]["apply"],"ACTIVE")
        self.assertEqual(self.ask(p,"cap1","CAPABILITIES")["fields"]["route_action"],"1")
        opposite=self.ask(p,"opposite","ACTION",
            self.fields("opposite",target="STOCK110",route="DIRECT111",generation="10"))
        self.assertEqual(opposite["fields"]["apply"],"PENDING")
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_CALLS\n"),b"HOST_ROUTE_CALLS=2\n")

    def test_no_ack_never_allows_a_competing_owner_request(self):
        self.env["MIBR_V3_HOST_ROUTE_NO_ACK"]="1"
        p=self.start("ui")
        self.assertEqual(self.ask(p,"lost","ACTION",self.fields("lost"))["fields"]["apply"],"PENDING")
        self.assertEqual(self.ask(p,"cap","CAPABILITIES")["fields"]["route_action"],"0")
        # Even a changed visible route/generation is insufficient without original RID ACK.
        self.assertEqual(self.ask(p,"state","STATUS")["fields"]["visible_route"],"DIRECT111")
        self.assertEqual(self.ask(p,"new","ACTION",
            self.fields("new",route="DIRECT111",target="STOCK110",generation="10"))["error"],"NOT_READY")
        self.assertEqual(self.ask(p,"poll","ACTION_STATUS",{"request_id":"lost"})["fields"]["apply"],"PENDING")
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_CALLS\n"),b"HOST_ROUTE_CALLS=1\n")

    def test_gateway_owner_and_independent_aid_full_mibr_action(self):
        self.env.pop("MIBR_V3_HOST_ROUTE_TEST")
        self.env["MIBR_V3_HOST_GATEWAY_TEST"]="1"
        p=self.start("ui")
        self.assertEqual(self.ask(p,"cap","CAPABILITIES")["fields"]["route_action"],"1")
        r=self.ask(p,"go","ACTION",self.fields("go"))
        self.assertEqual(r["fields"]["apply"],"ACTIVE")
        self.assertEqual(r["fields"]["visible_route"],"DIRECT111")
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_CALLS\n"),b"HOST_ROUTE_CALLS=1\n")
        self.assertEqual(self.ask(p,"now","STATUS")["fields"]["route_generation"],"10")
        self.assertEqual(self.ask(p,"go","ACTION",self.fields("go")),r)
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_CALLS\n"),b"HOST_ROUTE_CALLS=1\n")

    def test_gateway_aid_lag_blocks_action_until_original_ack(self):
        self.env.pop("MIBR_V3_HOST_ROUTE_TEST")
        self.env["MIBR_V3_HOST_GATEWAY_TEST"]="1"
        self.env["MIBR_V3_HOST_GATEWAY_AID_LAG"]="1"
        p=self.start("ui")
        r=self.ask(p,"lag","ACTION",self.fields("lag"))
        self.assertEqual(r["fields"]["apply"],"PENDING")
        self.assertEqual(self.ask(p,"cap","CAPABILITIES")["fields"]["route_action"],"0")
        self.assertEqual(self.ask(p,"status","STATUS")["fields"]["visible_route"],"UNKNOWN")
        self.assertEqual(self.ask(p,"other","ACTION",self.fields("other"))["error"],"NOT_READY")
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_CALLS\n"),b"HOST_ROUTE_CALLS=1\n")
        self.assertEqual(self.ask(p,"poll","ACTION_STATUS",{"request_id":"lag"})["fields"]["apply"],"PENDING")
        self.assertEqual(self.host_command(p,b"#HOST_AID_CATCHUP\n"),b"HOST_AID_CATCHUP_OK\n")
        self.assertEqual(self.ask(p,"poll2","ACTION_STATUS",{"request_id":"lag"})["fields"]["apply"],"ACTIVE")
        self.assertEqual(self.ask(p,"cap2","CAPABILITIES")["fields"]["route_action"],"1")
        self.assertEqual(self.ask(p,"fresh","STATUS")["fields"]["visible_route"],"DIRECT111")

    def test_gateway_owner_revoke_never_unlocks_pending_action(self):
        self.env.pop("MIBR_V3_HOST_ROUTE_TEST")
        self.env["MIBR_V3_HOST_GATEWAY_TEST"]="1"
        self.env["MIBR_V3_HOST_GATEWAY_AID_LAG"]="1"
        p=self.start("ui")
        self.assertEqual(self.ask(p,"lag","ACTION",self.fields("lag"))["fields"]["apply"],"PENDING")
        self.assertEqual(self.host_command(p,b"#HOST_GATEWAY_REVOKE\n"),b"HOST_GATEWAY_REVOKED\n")
        self.assertEqual(self.ask(p,"cap","CAPABILITIES")["fields"]["route_action"],"0")
        self.assertEqual(self.ask(p,"st","STATUS")["fields"]["visible_route"],"UNKNOWN")
        self.assertEqual(self.ask(p,"poll","ACTION_STATUS",{"request_id":"lag"})["fields"]["apply"],"PENDING")
        self.assertEqual(self.ask(p,"other","ACTION",self.fields("other"))["error"],"ACTIVATION_UNSUPPORTED")
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_CALLS\n"),b"HOST_ROUTE_CALLS=1\n")

    def test_uncertain_owner_result_remains_pending_and_single_inflight(self):
        self.env["MIBR_V3_HOST_ROUTE_UNCERTAIN"]="1"
        p=self.start("ui")
        first=self.ask(p,"uncertain","ACTION",self.fields("uncertain"))
        self.assertEqual(first["fields"]["apply"],"PENDING")
        self.assertEqual(first["fields"]["visible_route"],"UNKNOWN")
        self.assertEqual(self.ask(p,"cap","CAPABILITIES")["fields"]["route_action"],"0")
        self.assertEqual(self.ask(p,"retry","ACTION",self.fields("retry"))["error"],"NOT_READY")
        self.assertEqual(self.ask(p,"uncertain","ACTION",self.fields("uncertain")),first)
        self.assertEqual(self.ask(p,"poll","ACTION_STATUS",{"request_id":"uncertain"})["fields"]["apply"],"PENDING")
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_CALLS\n"),b"HOST_ROUTE_CALLS=1\n")
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_COMPLETE uncertain\n"),b"HOST_ROUTE_COMPLETE_OK\n")
        self.assertEqual(self.ask(p,"poll2","ACTION_STATUS",{"request_id":"uncertain"})["fields"]["apply"],"ACTIVE")
        self.assertEqual(self.ask(p,"cap2","CAPABILITIES")["fields"]["route_action"],"1")

    def test_proven_no_dispatch_does_not_create_pending_receipt(self):
        self.env["MIBR_V3_HOST_ROUTE_FAIL"]="1"
        p=self.start("ui")
        self.assertEqual(self.ask(p,"fail","ACTION",self.fields("fail"))["error"],"ACTIVATION_FAILED")
        self.assertEqual(self.ask(p,"cap","CAPABILITIES")["fields"]["route_action"],"1")
        self.assertEqual(self.ask(p,"poll","ACTION_STATUS",{"request_id":"fail"})["error"],"UNKNOWN_COMMIT")
        self.assertEqual(self.ask(p,"fail2","ACTION",self.fields("fail2"))["error"],"ACTIVATION_FAILED")
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_CALLS\n"),b"HOST_ROUTE_CALLS=2\n")

    def test_pending_does_not_become_active_without_owner_ack(self):
        self.env["MIBR_V3_HOST_ROUTE_PENDING"]="1"
        p=self.start("ui")
        a=self.ask(p,"go","ACTION",self.fields("go"))
        self.assertEqual(a["fields"]["apply"],"PENDING")
        self.assertEqual(a["fields"]["visible_route"],"UNKNOWN")
        self.assertEqual(self.ask(p,"now","STATUS")["fields"]["visible_route"],"STOCK110")
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_CALLS\n"),b"HOST_ROUTE_CALLS=1\n")
        pending=self.ask(p,"check","ACTION_STATUS",{"request_id":"go"})["fields"]
        self.assertEqual(pending["apply"],"PENDING")
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_COMPLETE go\n"),b"HOST_ROUTE_COMPLETE_OK\n")
        active=self.ask(p,"check2","ACTION_STATUS",{"request_id":"go"})["fields"]
        self.assertEqual((active["apply"],active["target"],active["receipt_scope"]),
                         ("ACTIVE","DIRECT111","HISTORICAL"))
        self.assertEqual(self.host_command(p,b"#HOST_ROUTE_CALLS\n"),b"HOST_ROUTE_CALLS=1\n")
        self.assertEqual(self.ask(p,"state2","STATUS")["fields"]["visible_route"],"DIRECT111")
        self.assertEqual(self.ask(p,"absent","ACTION_STATUS",{"request_id":"missing"})["error"],"UNKNOWN_COMMIT")
if __name__=="__main__":unittest.main()
