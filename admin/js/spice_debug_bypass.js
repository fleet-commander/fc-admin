/*
 * Copyright (C) 2014 Red Hat, Inc.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the licence, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this program; if not, see <http://www.gnu.org/licenses/>.
 *
 * Authors: Alberto Ruiz <aruiz@redhat.com>
 *          Oliver Gutiérrez <ogutierrez@redhat.com>
 */


SpiceConn.prototype.process_inbound = function(mb, saved_header) {
    DEBUG > 2 && console.log(this.type + ": processing message of size " + mb.byteLength + "; state is " + this.state);
    if (this.state == "ready")
    {
        if (saved_header == undefined)
        {
            var msg = new SpiceMiniData(mb);

            if (msg.type > 500)
            {
                console.error("Something has gone very wrong; we think we have message of type " + msg.type);
            }

            if (msg.size == 0)
            {
                this.process_message(msg);
                this.wire_reader.request(SpiceMiniData.prototype.buffer_size());
            }
            else
            {
                this.wire_reader.request(msg.size);
                this.wire_reader.save_header(msg);
            }
        }
        else
        {
            saved_header.data = mb;
            this.process_message(saved_header);
            this.wire_reader.request(SpiceMiniData.prototype.buffer_size());
            this.wire_reader.save_header(undefined);
        }
    }

    else if (this.state == "start")
    {
        this.reply_hdr = new SpiceLinkHeader(mb);
        if (this.reply_hdr.magic != SPICE_MAGIC)
        {
            this.state = "error";
            var e = new Error('Error: magic mismatch: ' + this.reply_hdr.magic);
            this.report_error(e);
        }
        else
        {
            // FIXME - Determine major/minor version requirements
            this.wire_reader.request(this.reply_hdr.size);
            this.state = "link";
        }
    }

    else if (this.state == "link")
    {
        this.reply_link = new SpiceLinkReply(mb);
         // FIXME - Screen the caps - require minihdr at least, right?
        if (this.reply_link.error)
        {
            this.state = "error";
            var e = new Error('Error: reply link error ' + this.reply_link.error);
            this.report_error(e);
        }
        else
        {
            this.send_ticket(rsa_encrypt(this.reply_link.pub_key, this.password + String.fromCharCode(0)));
            this.state = "ticket";
            this.wire_reader.request(SpiceLinkAuthReply.prototype.buffer_size());
        }
    }

    else if (this.state == "ticket")
    {
        this.auth_reply = new SpiceLinkAuthReply(mb);
        if (this.auth_reply.auth_code == SPICE_LINK_ERR_OK)
        {
            DEBUG > 0 && console.log(this.type + ': Connected');

            if (this.type == SPICE_CHANNEL_DISPLAY)
            {
                // FIXME - pixmap and glz dictionary config info?
                var dinit = new SpiceMsgcDisplayInit();
                var reply = new SpiceMiniData();
                reply.build_msg(SPICE_MSGC_DISPLAY_INIT, dinit);
                DEBUG > 0 && console.log("Request display init");
                this.send_msg(reply);
            }
            this.state = "ready";
            this.wire_reader.request(SpiceMiniData.prototype.buffer_size());
            if (this.timeout)
            {
                window.clearTimeout(this.timeout);
                delete this.timeout;
            }
        }
        else
        {
            this.state = "error";
            if (this.auth_reply.auth_code == SPICE_LINK_ERR_PERMISSION_DENIED)
            {
                var e = new Error("Permission denied.");
            }
            else
            {
                var e = new Error("Unexpected link error " + this.auth_reply.auth_code);
            }
            this.report_error(e);
        }
    }
}