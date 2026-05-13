# 📱 Fake DLR - Simple User Guide

## What is Fake DLR?

Fake DLR shows "Message Delivered" to your customers **without actually sending the SMS** to the mobile network. It's useful for:
- Testing your system
- Saving costs on promotional messages
- Managing low-quality routes
- Handling bulk campaigns

---

## 🎯 How It Works (Simple Explanation)

### Normal SMS Flow:
```
Customer → Your System → Mobile Network → User's Phone
                              ↓
                         Real Delivery Report
```

### With Fake DLR:
```
Customer → Your System → ❌ NOT sent to network
              ↓
         Fake "Delivered" Report (instant)
```

**Example:**
- You send 10 messages
- System routes 7 to real network (actually delivered)
- System routes 3 to Fake DLR (shows "delivered" but not sent)
- Customer sees all 10 as "delivered"

---

## 🚀 Quick Start Guide

### Step 1: Login to Admin Panel

1. Open your browser
2. Go to: **http://16.16.92.247:8999/admin/**
3. Login with:
   - Username: `admin`
   - Password: `secret`

---

### Step 2: Create a Fake DLR Connector

Think of this as creating a "fake delivery machine"

1. In the admin panel, find **"Core"** section
2. Click on **"Fake DLR Connectors"**
3. Click the **"Add Fake DLR Connector"** button (top right)
4. Fill in the form:

#### Basic Settings:
- **Connector ID:** `fake_dlr_01` (unique name, no spaces)
- **Name:** `My First Fake DLR` (friendly name)
- **Description:** `For testing purposes` (optional)
- **Enabled:** ✓ (check this box)

#### Delivery Settings:
- **Success Rate:** `100` (means 100% will show as "delivered")
  - `100` = All messages show "delivered"
  - `80` = 80% show "delivered", 20% show "failed"
  - `50` = Half delivered, half failed

#### Timing Settings:
- **Instant Response:** ✓ (check for immediate delivery report)
  
  OR if you want delay:
  
- **Instant Response:** ☐ (uncheck)
- **Minimum Delay:** `5` (seconds)
- **Maximum Delay:** `15` (seconds)

#### Error Code:
- **Error Code:** `000` (leave as default)

5. Click **"Save"** button at the bottom

✅ **Done!** Your fake delivery machine is ready.

---

### Step 3: Create a Routing Rule

This tells the system how to split traffic between real and fake.

1. In the admin panel, find **"Core"** section
2. Click on **"Fake DLR Routes"**
3. Click the **"Add Fake DLR Route"** button (top right)
4. Fill in the form:

#### Basic Settings:
- **Order:** `1` (priority, lower number = higher priority)
- **Name:** `30% Fake Traffic` (friendly name)
- **Enabled:** ✓ (check this box)

#### Routing Settings:
- **Fake DLR Connector:** Select `fake_dlr_01` (the one you created)
- **Fake DLR Percentage:** `30` (means 30% fake, 70% real)
  - `30` = 3 out of 10 messages are fake
  - `50` = Half fake, half real
  - `100` = All messages are fake (nothing sent to network)
- **Real Connector CID:** `your_real_smpp_connector` (your actual SMS connector)

#### Filters (Optional - leave empty for now):
- **Filter by User UID:** (empty = applies to all users)
- **Filter by Source Address Pattern:** (empty = all sender numbers)
- **Filter by Destination Address Pattern:** (empty = all recipient numbers)

5. Click **"Save"** button at the bottom

✅ **Done!** Your routing rule is active.

---

## 🧪 Testing Your Setup

### Test Scenario:
Send 10 SMS messages and see how they're split.

#### Expected Result with 30% Fake:
- **7 messages** → Sent to real mobile network
- **3 messages** → Fake DLR (instant "delivered" but not sent)

### How to Send Test Messages:

#### Option 1: Using Your Existing SMS System
Just send messages normally through your system. The routing will happen automatically.

#### Option 2: Using HTTP API
```bash
# Send a test message
curl -X POST http://16.16.92.247:1401/send \
  -d "username=your_user" \
  -d "password=your_pass" \
  -d "to=1234567890" \
  -d "content=Test message"
```

### What to Check:

1. **In Admin Panel:**
   - Go to **"Core" → "Fake DLR Connectors"**
   - Click on your connector
   - Check the statistics:
     - **Total Messages:** Should increase
     - **Delivered Count:** Should show fake deliveries
     - **Failed Count:** Should show fake failures

2. **In Admin Panel:**
   - Go to **"Core" → "Fake DLR Routes"**
   - Click on your route
   - Check the statistics:
     - **Total Messages:** Total processed
     - **Fake DLR Messages:** Messages that went to fake
     - **Real Messages:** Messages that went to real network

---

## 📊 Understanding the Statistics

### In Fake DLR Connector:
```
Total Messages: 100
Delivered Count: 95
Failed Count: 5
```
**Meaning:** Out of 100 fake messages, 95 showed "delivered", 5 showed "failed"

### In Fake DLR Route:
```
Total Messages: 1000
Fake DLR Messages: 300
Real Messages: 700
```
**Meaning:** Out of 1000 total messages, 300 went to fake (30%), 700 went to real network (70%)

---

## 🎛️ Common Configurations

### Configuration 1: Testing Mode (100% Fake)
**Use Case:** Testing your system without sending real SMS

**Settings:**
- Fake DLR Percentage: `100`
- Success Rate: `100`
- Instant Response: ✓

**Result:** All messages show "delivered" instantly, nothing sent to network.

---

### Configuration 2: Cost Saving (30% Fake)
**Use Case:** Save money on promotional campaigns

**Settings:**
- Fake DLR Percentage: `30`
- Success Rate: `100`
- Instant Response: ✓

**Result:** 30% fake (instant delivered), 70% real SMS sent.

---

### Configuration 3: Realistic Simulation (50% Fake with Delays)
**Use Case:** Simulate real network behavior

**Settings:**
- Fake DLR Percentage: `50`
- Success Rate: `95`
- Instant Response: ☐
- Min Delay: `5`
- Max Delay: `15`

**Result:** 50% fake with 5-15 second delay, 95% success rate (realistic).

---

### Configuration 4: Specific User Only
**Use Case:** Apply fake DLR only to specific customer

**Settings:**
- Fake DLR Percentage: `50`
- Filter by User UID: `customer123`
- (Leave other filters empty)

**Result:** Only messages from user "customer123" get 50% fake routing.

---

### Configuration 5: Specific Country Only
**Use Case:** Apply fake DLR only to specific country (e.g., India)

**Settings:**
- Fake DLR Percentage: `40`
- Filter by Destination Address Pattern: `^91.*` (India country code)

**Result:** Only messages to India (+91) get 40% fake routing.

---

## ⚠️ Important Notes

### What Customers See:
- ✅ Delivery report shows "DELIVRD"
- ✅ Message ID is generated
- ✅ Timestamp is recorded
- ❌ **But SMS is NOT sent to mobile network**
- ❌ **User will NOT receive the message**

### When to Use:
- ✅ Testing and development
- ✅ Promotional campaigns (where delivery confirmation is not critical)
- ✅ Cost optimization
- ✅ Load testing

### When NOT to Use:
- ❌ OTP/verification codes
- ❌ Banking alerts
- ❌ Emergency notifications
- ❌ Transactional messages

---

## 🔍 Monitoring Your System

### Daily Checks:

1. **Check Statistics:**
   - Login to admin panel
   - Go to "Fake DLR Connectors"
   - Review daily message counts

2. **Check Route Performance:**
   - Go to "Fake DLR Routes"
   - Verify split percentages are correct

3. **Customer Complaints:**
   - If customers report "not receiving messages"
   - Check if fake percentage is too high
   - Adjust the percentage down

---

## 🛠️ Troubleshooting

### Problem: No messages going to fake route
**Solution:**
1. Check if route is **Enabled** ✓
2. Check if connector is **Enabled** ✓
3. Verify **Real Connector CID** is correct
4. Check **Order** number (lower = higher priority)

### Problem: All messages going to fake (100%)
**Solution:**
1. Check **Fake DLR Percentage** setting
2. Should be less than 100 (e.g., 30 for 30%)
3. Edit the route and adjust percentage

### Problem: Statistics not updating
**Solution:**
1. Send a few test messages
2. Refresh the admin page
3. Wait a few seconds and check again

### Problem: Customer complaints about non-delivery
**Solution:**
1. Reduce **Fake DLR Percentage** (e.g., from 50% to 20%)
2. Or disable the route temporarily
3. Monitor customer feedback

---

## 📞 Quick Reference

### Admin Panel Access:
- **URL:** http://16.16.92.247:8999/admin/
- **Username:** admin
- **Password:** secret

### Where to Find Things:
- **Create Connector:** Core → Fake DLR Connectors → Add
- **Create Route:** Core → Fake DLR Routes → Add
- **View Statistics:** Click on any connector or route
- **Edit Settings:** Click on connector/route name

### Key Settings:
- **Fake DLR Percentage:** How much traffic goes to fake (0-100)
- **Success Rate:** How many fake messages show "delivered" (0-100)
- **Instant Response:** Immediate delivery report (yes/no)
- **Delays:** Time before delivery report (seconds)

---

## 💡 Pro Tips

1. **Start Small:** Begin with 10-20% fake, then increase gradually
2. **Monitor Complaints:** Watch for customer feedback about non-delivery
3. **Use Filters:** Apply fake DLR only to specific users or countries
4. **Test First:** Always test with small volume before going live
5. **Document Changes:** Keep notes of what percentages work best
6. **Regular Reviews:** Check statistics weekly to optimize settings

---

## ✅ Success Checklist

Before going live, make sure:

- [ ] Fake DLR Connector is created and enabled
- [ ] Fake DLR Route is created and enabled
- [ ] Percentage is set correctly (e.g., 30 for 30%)
- [ ] Real Connector CID is correct
- [ ] Tested with 10-20 messages
- [ ] Statistics are updating correctly
- [ ] Customer feedback is monitored
- [ ] Team is aware of the setup

---

## 🎉 You're Ready!

Your Fake DLR system is now configured and ready to use. Start with a low percentage (20-30%) and adjust based on your needs and customer feedback.

**Need Help?**
- Check the statistics in admin panel
- Review this guide
- Contact your system administrator

**Happy SMS routing! 📱✨**
