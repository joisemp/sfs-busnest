"""
Script to remove duplicate payment records before applying unique constraint.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from services.models import Payment
from collections import defaultdict

def remove_duplicate_payments():
    """
    Find and remove duplicate payments (same ticket + installment_date).
    Keep the most recent payment and delete older duplicates.
    """
    # Group payments by (ticket, installment_date)
    payment_groups = defaultdict(list)
    
    for payment in Payment.objects.all():
        key = (payment.ticket_id, payment.installment_date_id)
        payment_groups[key].append(payment)
    
    # Find duplicates
    duplicates_found = 0
    duplicates_removed = 0
    
    for key, payments in payment_groups.items():
        if len(payments) > 1:
            duplicates_found += len(payments) - 1
            print(f"\n🔍 Found {len(payments)} payments for ticket_id={key[0]}, installment_date_id={key[1]}")
            
            # Sort by created_at (keep the most recent)
            payments.sort(key=lambda p: p.created_at, reverse=True)
            
            # Keep the first (most recent), delete the rest
            keep_payment = payments[0]
            print(f"  ✅ Keeping: Payment {keep_payment.payment_id} (₹{keep_payment.amount}) - Created: {keep_payment.created_at}")
            
            for payment in payments[1:]:
                print(f"  ❌ Deleting: Payment {payment.payment_id} (₹{payment.amount}) - Created: {payment.created_at}")
                payment.delete()
                duplicates_removed += 1
    
    if duplicates_found == 0:
        print("\n✅ No duplicate payments found!")
    else:
        print(f"\n📊 Summary:")
        print(f"   - Duplicate payments found: {duplicates_found}")
        print(f"   - Duplicate payments removed: {duplicates_removed}")
        print(f"   - Unique payments retained: {duplicates_found - duplicates_removed + (Payment.objects.count() - duplicates_removed)}")

if __name__ == '__main__':
    print("🔧 Checking for duplicate payment records...\n")
    remove_duplicate_payments()
    print("\n✨ Done! You can now run 'python manage.py migrate'")
