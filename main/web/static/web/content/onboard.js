(function($){
    var csrf = document.getElementsByName('csrfmiddlewaretoken')[0].value;
    function esc(s){ return $('<div>').text(s == null ? '' : String(s)).html(); }

    // Populate existing groups (newest first, matching the Sort Recent behaviour).
    $.ajax({ url: main_trans.url2groups, type: "POST", dataType: "json",
        data: { csrfmiddlewaretoken: csrf, s: "list" },
        success: function(d){
            var opts = (d.groups || []).slice().reverse().map(function(g){
                return '<option value="'+esc(g.name)+'">'+esc(g.name)+'</option>';
            }).join('');
            $("#gid_existing").html(opts || '<option value="">(no groups yet — choose "Create new")</option>');
        }
    });

    // Populate SMPP connectors, flagging the ones that are actually bound.
    $.ajax({ url: main_trans.url2smppccm, type: "POST", dataType: "json",
        data: { csrfmiddlewaretoken: csrf, s: "list" },
        success: function(d){
            var opts = (d.connectors || []).slice().reverse().map(function(c){
                var bound = /^BOUND/.test(c.session || "");
                return '<option value="'+esc(c.cid)+'">'+esc(c.cid)+(bound ? ' — connected' : ' — not connected')+'</option>';
            }).join('');
            $("#connector").html(opts || '<option value="">(no connectors)</option>');
        }
    });

    $('input[name=group_mode]').on('change', function(){
        if ($(this).val() === 'new') { $("#gid_existing").hide(); $("#gid_new").show(); }
        else { $("#gid_new").hide(); $("#gid_existing").show(); }
    });

    $(document).on('click', '.toggle-password', function(e){
        e.preventDefault();
        var $i = $(this).closest('.input-group').find('.password-input');
        var $ic = $(this).find('i');
        if ($i.attr('type') === 'password') { $i.attr('type', 'text'); $ic.removeClass('fa-eye').addClass('fa-eye-slash'); }
        else { $i.attr('type', 'password'); $ic.removeClass('fa-eye-slash').addClass('fa-eye'); }
    });

    function renderSteps(steps){
        return (steps || []).map(function(s){
            var icon = s.ok
                ? '<i class="fas fa-check-circle text-success mr-1"></i>'
                : '<i class="fas fa-times-circle text-danger mr-1"></i>';
            return '<div class="step-line">'+icon+'<strong>'+esc(s.step)+'</strong> — '+esc(s.detail)+'</div>';
        }).join('');
    }

    function resetBtn($btn){ $btn.prop('disabled', false).html('<i class="fas fa-user-plus mr-1"></i>Create customer'); }

    $("#onboard_form").on('submit', function(e){
        e.preventDefault();
        var mode = $('input[name=group_mode]:checked').val();
        var gid = mode === 'new' ? $("#gid_new").val() : $("#gid_existing").val();
        var payload = {
            csrfmiddlewaretoken: csrf, s: "create",
            group_mode: mode, gid: gid,
            uid: $("input[name=uid]").val(),
            username: $("input[name=username]").val(),
            password: $("input[name=password]").val(),
            balance: $("input[name=balance]").val(),
            smpps_throughput: $("input[name=smpps_throughput]").val(),
            http_throughput: $("input[name=http_throughput]").val(),
            connector: $("#connector").val(),
            rate: $("input[name=rate]").val()
        };
        var $btn = $("#onboard_submit").prop('disabled', true).html('<i class="fas fa-spinner fa-spin mr-1"></i>Working…');
        $("#onboard_result").html('<div class="text-muted"><i class="fas fa-spinner fa-spin mr-1"></i>Creating…</div>');
        $.ajax({ url: main_trans.url2onboard, type: "POST", data: payload, dataType: "json",
            success: function(d){
                $("#onboard_result").html(renderSteps(d.steps) + '<div class="alert alert-success mt-2 mb-0">'+esc(d.message)+'</div>');
                toastr.success(d.message, { closeButton: true, progressBar: true });
                resetBtn($btn);
            },
            error: function(jqXHR){
                var r = {};
                try { r = JSON.parse(jqXHR.responseText); } catch (err) {}
                $("#onboard_result").html(renderSteps(r.steps) + '<div class="alert alert-danger mt-2 mb-0">'+esc(r.message || 'Failed')+'</div>');
                toastr.error(r.message || 'Failed', { closeButton: true, progressBar: true });
                resetBtn($btn);
            }
        });
    });

    $("li.nav-item.onboard-menu").addClass("active");
})(jQuery);
