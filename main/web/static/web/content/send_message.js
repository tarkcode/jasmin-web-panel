(function($){
    var csrfmiddlewaretoken = document.getElementsByName('csrfmiddlewaretoken')[0].value;
    
    // Fetch users from gateway
    function loadGatewayUsers() {
        $.ajax({
            url: window.location.pathname + 'manage/',
            type: "POST",
            data: {
                csrfmiddlewaretoken: csrfmiddlewaretoken,
                s: "list_users"
            },
            dataType: "json",
            success: function(data){
                if (data.users && data.users.length > 0) {
                    var options = '<option value="">Default (Environment Credentials)</option>';
                    data.users.forEach(function(user){
                        // Only show enabled users
                        if (user.status === 'enabled') {
                            options += '<option value="' + user.uid + '">' + 
                                      user.uid + ' (' + user.username + ')</option>';
                        }
                    });
                    $('#user_uid').html(options);
                } else {
                    $('#user_uid').html('<option value="">Default (Environment Credentials)</option>');
                }
            },
            error: function(jqXHR, textStatus, errorThrown){
                console.error('Failed to load gateway users:', textStatus);
                $('#user_uid').html('<option value="">Default (Environment Credentials)</option>');
            }
        });
    }
    
    // Load users on page load
    loadGatewayUsers();

    // ---- SMS segment / encoding / cost calculator ----
    var $text = $("#text"), $enc = $("#sms_enc"), $chars = $("#sms_chars"),
        $segs = $("#sms_segs"), $remain = $("#sms_remain"), $warn = $("#sms_warn"),
        $normWrap = $("#sms_norm_wrap"), $normHint = $("#sms_norm_hint"),
        $rate = $("#sms_rate"), $cost = $("#sms_cost");

    function fmtChar(c){
        if (c === " ") return "space";
        var cp = c.codePointAt(0);
        if (cp < 0x20) return "\\u" + cp.toString(16);
        return c;
    }
    function trimNum(n){
        return n.toFixed(4).replace(/\.?0+$/, "") || "0";
    }
    function updateSmsCalc(){
        if (!window.SmsSegments || !$text.length) return;
        var r = window.SmsSegments.analyze($text.val());
        $enc.text(r.encoding).toggleClass("ucs2", !r.isGsm);
        $chars.html("<strong>" + r.chars + "</strong> chars");
        $segs.html("<strong>" + r.segments + "</strong> segment" + (r.segments === 1 ? "" : "s"));
        $remain.text(r.segments === 0 ? "" :
            (r.remaining + " left in " + (r.segments === 1 ? "this segment" : "last segment")));
        var rate = parseFloat($rate.val()) || 0;
        $cost.text(trimNum(rate * r.segments));
        if (!r.isGsm) {
            var sample = r.nonGsm.slice(0, 8).map(fmtChar).join("  ");
            $warn.show().html('<i class="fas fa-exclamation-triangle mr-1"></i>' +
                'This message uses <strong>Unicode (UCS-2)</strong> — the limit drops to <strong>70</strong> chars/segment, ' +
                'so it will be sent as <strong>' + r.segments + ' segment' + (r.segments === 1 ? '' : 's') +
                '</strong> and billed accordingly.<br>Character' + (r.nonGsm.length === 1 ? '' : 's') +
                ' forcing Unicode: <code>' + sample + '</code>' + (r.nonGsm.length > 8 ? ' …' : ''));
            $normWrap.show();
        } else {
            $warn.hide();
            $normWrap.hide();
            $normHint.text("");
        }
    }
    $text.on("input", updateSmsCalc);
    $rate.on("input", updateSmsCalc);
    $("#sms_normalize").on("click", function(){
        var res = window.SmsSegments.normalize($text.val());
        $text.val(res.text);
        var bits = [];
        if (res.replaced) bits.push(res.replaced + " replaced");
        if (res.stripped) bits.push(res.stripped + " removed (can't be converted, e.g. emoji)");
        $normHint.text(bits.length ? "(" + bits.join(", ") + ")" : "(already GSM-7)");
        updateSmsCalc();
    });
    updateSmsCalc();

    $("li.nav-item.send-sms-menu").addClass("active");
})(jQuery);