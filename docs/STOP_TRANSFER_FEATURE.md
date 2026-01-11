# Stop Transfer Feature - Drag and Drop

## Overview
This feature provides a drag-and-drop interface for transferring stops between routes. When a stop is moved from one route to another, all associated tickets are automatically updated, and trip booking counts are recalculated to maintain data integrity.

## Features

### 1. Visual Drag-and-Drop Interface
- **Intuitive Design**: Displays all routes in a grid layout with their stops
- **Responsive**: Works on desktop, tablet, and mobile devices
- **Visual Feedback**: Highlights drop zones when dragging, shows dragging state
- **Real-time Updates**: UI updates immediately after successful transfer

### 2. Inline Stop Name Editing
- **Double-Click to Edit**: Double-click any stop name to edit it inline
- **Instant Save**: Press Enter to save or Esc to cancel
- **Auto-Save**: Clicking outside the input field saves automatically
- **Validation**: Ensures stop name is 2-200 characters
- **Activity Logging**: All name changes are logged for audit trail

### 3. Automatic Ticket Management
- **Ticket Updates**: All tickets referencing the transferred stop are updated
- **Bus Record Assignment**: Tickets are reassigned to valid bus records on the target route
- **Schedule Preservation**: Pickup and drop schedules remain intact
- **Validation**: Ensures bus capacity is not exceeded before transfer

### 4. Trip Count Recalculation
- **Automatic Decrement**: Decreases booking counts on old route's trips
- **Automatic Increment**: Increases booking counts on new route's trips
- **Capacity Check**: Validates available capacity before allowing transfer
- **Min Required Capacity**: Updates BusRecord.min_required_capacity as needed

## File Structure

```
src/
├── services/
│   ├── views/
│   │   └── central_admin.py
│   │       ├── StopTransferManagementView (GET - displays interface)
│   │       └── TransferStopAPIView (POST - handles transfer)
│   ├── urls/
│   │   └── central_admin.py
│   │       ├── stop_transfer_management/ (main page)
│   │       └── transfer_stop_api/ (AJAX endpoint)
│   └── utils/
│       └── transfer_stop.py
│           └── move_stop_and_update_tickets() (core logic)
├── templates/
│   └── central_admin/
│       └── stop_transfer_management.html (main template)
└── static/
    ├── js/
    │   └── stop_transfer.js (drag-and-drop logic)
    └── styles/
        └── central_admin/
            └── stop_transfer/
                ├── style.scss (source styles)
                └── style.css (compiled styles)
```

## How to Use

### For Users
1. Navigate to a registration's route list page
2. Click the **"Transfer Stops"** button (yellow button with arrows icon)
3. You'll see all routes displayed in a grid
4. **To Transfer a Stop:**
   - Drag a stop from one route and drop it onto another route's drop zone
   - Confirm the transfer in the popup dialog
   - The system will move the stop and update all tickets
5. **To Edit a Stop Name:**
   - Double-click on any stop name
   - Type the new name
   - Press Enter to save or Esc to cancel
   - Click outside to auto-save
6. The system will:
   - Move the stop to the new route (if transferring)
   - Update all associated tickets
   - Recalculate trip booking counts
   - Show success message with details

### Access Control
- **Role**: Central Admin only
- **Registration Status**: Works only when registration is closed
- **Organization Scoping**: Users can only transfer stops within their organization

## Technical Details

### Backend (Python/Django)

#### StopTransferManagementView
```python
URL: /central_admin/registrations/<registration_slug>/stops/transfer-management/
Method: GET
Returns: HTML page with all routes and their stops
```

#### TransferStopAPIView
```python
URL: /central_admin/registrations/<registration_slug>/stops/transfer-api/
Method: POST
Content-Type: application/json

Request Body:
{
    "stop_slug": "string",
    "target_route_slug": "string"
}

Response (Success):
{
    "success": true,
    "message": "Stop 'X' successfully transferred from 'Route A' to 'Route B'...",
    "stop": {
        "slug": "string",
        "name": "string",
        "new_route_slug": "string",
        "new_route_name": "string"
    },
    "source_route": {
        "slug": "string",
        "stop_count": number
    },
    "target_route": {
        "slug": "string",
        "stop_count": number
    }
}

Response (Error):
{
    "success": false,
    "message": "Error message"
}
```

#### UpdateStopNameAPIView
```python
URL: /central_admin/registrations/<registration_slug>/stops/update-name-api/
Method: POST
Content-Type: application/json

Request Body:
{
    "stop_slug": "string",
    "new_name": "string"
}

Response (Success):
{
    "success": true,
    "message": "Stop renamed from 'Old Name' to 'New Name' successfully",
    "stop": {
        "slug": "string",
        "name": "string",
        "old_name": "string",
        "route_slug": "string",
        "route_name": "string"
    }
}

Response (Error):
{
    "success": false,
    "message": "Error message"
}

Validations:
- Name must be 2-200 characters
- Name cannot be the same as current name
- Name is trimmed of whitespace
```

### Transfer Logic (move_stop_and_update_tickets)

The utility function in `services/utils/transfer_stop.py` handles the complex transfer logic:

1. **Validation Phase**:
   - Finds all tickets referencing the stop (pickup or drop)
   - Identifies available bus records on the target route
   - Checks if trips exist for required schedules
   - Validates bus capacity won't be exceeded

2. **Assignment Phase**:
   - Maps each ticket to a suitable bus record on target route
   - Ensures capacity constraints are met
   - Tracks booking count changes

3. **Execution Phase** (Atomic Transaction):
   - Decrements booking counts on old trips
   - Increments booking counts on new trips
   - Updates ticket bus record assignments
   - Moves the stop to the new route
   - Saves all changes

### Frontend (JavaScript)

#### Event Handlers
- `handleDragStart`: Stores dragged stop data, adds visual feedback, prevents dragging while editing
- `handleDragEnd`: Cleans up visual states
- `handleDragOver`: Required to allow dropping
- `handleDragEnter`: Highlights valid drop zones
- `handleDragLeave`: Removes highlight when leaving drop zone
- `handleDrop`: Validates and initiates transfer
- `handleStopNameEdit`: Activates inline editing mode on double-click
- `saveStopName`: Sends API request to update stop name
- `cancelEdit`: Cancels editing and restores original state

#### AJAX Communication
- Uses Fetch API for modern async requests
- Includes CSRF token for security
- Handles success/error responses
- Updates UI without page reload
- Separate endpoints for transfer and name update

### Styling (SCSS/CSS)

Key visual elements:
- **Route Cards**: Grid layout with responsive breakpoints
- **Drop Zones**: Highlight on drag-over with dashed border
- **Stop Items**: Draggable with grab cursor and hover effects
- **Stop Names**: Clickable with hover effect, tooltip indicates double-click to edit
- **Inline Input**: Styled input field with focus states and shadow
- **Drag Feedback**: Opacity change and scale transform when dragging
- **Loading Overlay**: Modal spinner during transfer
- **Notifications**: Sticky alert at top with auto-dismiss

## Error Handling

### Validation Errors
- **Same Route**: Cannot drop stop onto its current route
- **No Bus Records**: Target route must have bus records with trips
- **Capacity Exceeded**: All bus records on target route are full
- **Missing Trips**: No trips found for ticket's schedules on target route

### User Feedback
- **Confirmation Dialog**: Prevents accidental transfers
- **Success Message**: Shows stop name, source/target routes, and counts updated
- **Error Messages**: Clear explanation of why transfer failed
- **Loading State**: Visual feedback during async operation

## Security

- **CSRF Protection**: All POST requests include CSRF token
- **Authentication**: LoginRequiredMixin ensures user is logged in
- **Authorization**: CentralAdminOnlyAccessMixin restricts to central admins
- **Organization Scoping**: All queries filtered by `user.profile.org`
- **Registration State**: RegistrationClosedOnlyAccessMixin prevents changes to open registrations

## Activity Logging

Every successful transfer is logged:
```python
log_user_activity(
    user=request.user,
    action="Transferred stop via drag-and-drop",
    description=f"Moved stop '{stop.name}' from route '{source}' to route '{target}'"
)
```

## Browser Compatibility

- **HTML5 Drag and Drop API**: Supported in all modern browsers
- **Chrome**: ✅ Full support
- **Firefox**: ✅ Full support
- **Safari**: ✅ Full support
- **Edge**: ✅ Full support
- **Mobile**: ✅ Touch events handled

## Performance Considerations

- **Atomic Transactions**: Uses Django's `@transaction.atomic` to ensure data integrity
- **Prefetch Related**: Routes prefetch their stops to minimize queries
- **Bulk Operations**: Trip updates happen efficiently within single transaction
- **Minimal Reloads**: UI updates via JavaScript without page refresh

## Testing Checklist

### Manual Testing
- [ ] Can access the stop transfer management page
- [ ] All routes and stops are displayed correctly
- [ ] Stop counts are accurate
- [ ] Can drag a stop successfully
- [ ] Drop zones highlight on drag-over
- [ ] Cannot drop on same route (shows warning)
- [ ] Confirmation dialog appears before transfer
- [ ] Transfer succeeds and shows success message
- [ ] UI updates correctly (stop moves, counts update)
- [ ] Empty route shows "No stops" message
- [ ] Loading overlay appears during transfer
- [ ] Error messages display for failed transfers
- [ ] **Can double-click stop name to edit**
- [ ] **Input field appears with current name selected**
- [ ] **Can save with Enter key**
- [ ] **Can cancel with Esc key**
- [ ] **Auto-saves when clicking outside**
- [ ] **Name validation works (2-200 chars)**
- [ ] **Success message shows old and new name**
- [ ] **Cannot edit while dragging**
- [ ] **Cannot drag while editing**

### Data Integrity Testing
- [ ] Tickets are updated with new bus records
- [ ] Old trip booking counts decrease
- [ ] New trip booking counts increase
- [ ] BusRecord.min_required_capacity updates
- [ ] Stop.route changes to target route
- [ ] Activity log entry created

### Edge Cases
- [ ] Transfer stop with many tickets (100+)
- [ ] Transfer when target route bus is near capacity
- [ ] Transfer one-way ticket stop (only pickup or drop)
- [ ] Transfer two-way ticket stop
- [ ] Multiple rapid transfers (rate limiting)
- [ ] Transfer with concurrent modifications

## Future Enhancements

### Possible Improvements
1. **Batch Transfer**: Select multiple stops and transfer together
2. **Undo Feature**: Revert last transfer within time window
3. **Transfer History**: View log of all stop transfers
4. **Drag Preview**: Show stop card while dragging
5. **Search/Filter**: Find specific stops across routes
6. **Route Sorting**: Reorder routes by name/stop count
7. **Mobile Gestures**: Improved touch handling for tablets
8. **Validation Preview**: Show capacity check before confirming

## Troubleshooting

### Common Issues

**Issue**: Stop won't drop on target route
- **Solution**: Ensure registration is closed, you're logged in as central admin

**Issue**: "Capacity exceeded" error
- **Solution**: Target route's buses are full. Assign more buses or increase capacity

**Issue**: "No suitable bus record" error
- **Solution**: Create bus records with trips matching the ticket's schedules on target route

**Issue**: Styles not loading
- **Solution**: Compile SCSS: `sass style.scss style.css` in stop_transfer folder

**Issue**: JavaScript not working
- **Solution**: Check browser console for errors, ensure stop_transfer.js is loaded

## Support

For issues or questions about this feature:
1. Check the error message in the notification
2. Review browser console for JavaScript errors
3. Check Django logs for backend errors
4. Verify registration is closed and user has central admin role
5. Ensure all migrations are applied

---

**Version**: 1.0  
**Last Updated**: October 27, 2025  
**Author**: SFS BusNest Development Team
