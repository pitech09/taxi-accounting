"""
Settlement views – shared logic for owner and driver portals.

Most settlement operations are handled by owner/views.py and driver_portal/views.py.
This module provides shared views for reporting, admin overrides, and API‑like endpoints.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
import csv

from settlements.models import DailySettlement
from settlements.forms import SettlementAdminForm  # we'll create this
from vehicles.models import Vehicle
from drivers.models import Driver


# ------------------------------------------------------------------
# Helper: check if user is owner (staff/superuser)
# ------------------------------------------------------------------
def is_owner(user):
    """Return True if user is staff or superuser."""
    return user.is_staff or user.is_superuser


# ------------------------------------------------------------------
# List view (owner only – with filters)
# ------------------------------------------------------------------
@login_required
@user_passes_test(is_owner)
def settlement_list(request):
    """
    List all settlements with filtering and pagination.
    Accessible only to owners (staff/superuser).
    """
    settlements = DailySettlement.objects.select_related(
        'driver', 'vehicle'
    ).order_by('-date', '-created_at')

    # Filters
    status = request.GET.get('status')
    if status:
        settlements = settlements.filter(status=status)

    vehicle_id = request.GET.get('vehicle')
    if vehicle_id:
        settlements = settlements.filter(vehicle_id=vehicle_id)

    driver_id = request.GET.get('driver')
    if driver_id:
        settlements = settlements.filter(driver_id=driver_id)

    start_date = request.GET.get('start_date')
    if start_date:
        settlements = settlements.filter(date__gte=start_date)

    end_date = request.GET.get('end_date')
    if end_date:
        settlements = settlements.filter(date__lte=end_date)

    # Pagination
    paginator = Paginator(settlements, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'settlements': page_obj,
        'statuses': DailySettlement.STATUS_CHOICES,
        'vehicles': Vehicle.objects.filter(is_active=True),
        'drivers': Driver.objects.filter(is_active=True),
        'current_status': status,
        'current_vehicle': vehicle_id,
        'current_driver': driver_id,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'owner/settlements/list.html', context)


# ------------------------------------------------------------------
# Detail view (owner only)
# ------------------------------------------------------------------
@login_required
@user_passes_test(is_owner)
def settlement_detail(request, pk):
    """
    View a single settlement in detail.
    """
    settlement = get_object_or_404(
        DailySettlement.objects.select_related('driver', 'vehicle', 'approved_by'),
        pk=pk
    )
    context = {
        'settlement': settlement,
        'can_edit': settlement.status not in ['approved', 'rejected'],
    }
    return render(request, 'owner/settlements/detail.html', context)


# ------------------------------------------------------------------
# Admin create view (owner override – creates on behalf of driver)
# ------------------------------------------------------------------
@login_required
@user_passes_test(is_owner)
def settlement_create_admin(request):
    """
    Admin view to create a settlement on behalf of a driver.
    Useful for owners who want to enter settlements manually.
    """
    if request.method == 'POST':
        form = SettlementAdminForm(request.POST)
        if form.is_valid():
            settlement = form.save(commit=False)
            settlement.status = 'submitted'  # still needs approval
            settlement.submitted_at = timezone.now()
            settlement.save()
            messages.success(request, f'Settlement for {settlement.driver.name} created and submitted for approval.')
            return redirect('settlements:detail', pk=settlement.pk)
    else:
        form = SettlementAdminForm(initial={'date': timezone.now().date()})

    context = {'form': form}
    return render(request, 'owner/settlements/form.html', context)


# ------------------------------------------------------------------
# Admin edit view (owner override)
# ------------------------------------------------------------------
@login_required
@user_passes_test(is_owner)
def settlement_edit_admin(request, pk):
    """
    Admin view to edit a settlement (only if not approved).
    """
    settlement = get_object_or_404(DailySettlement, pk=pk)

    if settlement.status == 'approved':
        messages.error(request, 'Cannot edit an approved settlement.')
        return redirect('settlements:detail', pk=pk)

    if request.method == 'POST':
        form = SettlementAdminForm(request.POST, instance=settlement)
        if form.is_valid():
            form.save()
            messages.success(request, f'Settlement for {settlement.driver.name} updated.')
            return redirect('settlements:detail', pk=pk)
    else:
        form = SettlementAdminForm(instance=settlement)

    context = {
        'form': form,
        'settlement': settlement,
    }
    return render(request, 'owner/settlements/form.html', context)


# ------------------------------------------------------------------
# Approve / Reject view
# ------------------------------------------------------------------
@login_required
@user_passes_test(is_owner)
def settlement_approve(request, pk):
    """
    Approve or reject a settlement.
    - Approval: runs calculations, creates cash transaction.
    - Rejection: returns to driver for editing.
    """
    settlement = get_object_or_404(DailySettlement, pk=pk)

    if settlement.status == 'approved':
        messages.warning(request, 'Settlement is already approved.')
        return redirect('settlements:detail', pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')
        owner_notes = request.POST.get('owner_notes', '')

        if action == 'approve':
            settlement.status = 'approved'
            settlement.approved_at = timezone.now()
            settlement.approved_by = request.user
            settlement.owner_notes = owner_notes
            settlement.save()  # triggers calculations + cash transaction
            messages.success(
                request,
                f'Settlement for {settlement.driver.name} approved! '
                f'Owner collection: M {settlement.total_owner_collected:.2f} added to cash.'
            )
        elif action == 'reject':
            settlement.status = 'rejected'
            settlement.owner_notes = owner_notes
            settlement.save()
            messages.warning(
                request,
                f'Settlement for {settlement.driver.name} rejected. '
                'Driver can edit and resubmit.'
            )
        else:
            messages.error(request, 'Invalid action.')
            return redirect('settlements:detail', pk=pk)

        return redirect('settlements:list')

    context = {
        'settlement': settlement,
        'model_display': settlement.get_operating_model_display(),
    }
    return render(request, 'owner/approvals/review.html', context)


# ------------------------------------------------------------------
# Export settlements to CSV (owner only)
# ------------------------------------------------------------------
@login_required
@user_passes_test(is_owner)
def settlement_export_csv(request):
    """
    Export all settlements (filtered) to CSV.
    """
    settlements = DailySettlement.objects.select_related(
        'driver', 'vehicle'
    ).order_by('-date')

    # Apply same filters as list view
    status = request.GET.get('status')
    if status:
        settlements = settlements.filter(status=status)

    vehicle_id = request.GET.get('vehicle')
    if vehicle_id:
        settlements = settlements.filter(vehicle_id=vehicle_id)

    driver_id = request.GET.get('driver')
    if driver_id:
        settlements = settlements.filter(driver_id=driver_id)

    start_date = request.GET.get('start_date')
    if start_date:
        settlements = settlements.filter(date__gte=start_date)

    end_date = request.GET.get('end_date')
    if end_date:
        settlements = settlements.filter(date__lte=end_date)

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="settlements_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Date', 'Driver', 'Vehicle', 'Model',
        'Total Income', 'Total Expenses', 'Gross Profit',
        'Driver Pay', 'Owner Collection', 'Debt Repaid', 'New Debt',
        'Status', 'Approved By', 'Approved At'
    ])

    for s in settlements:
        writer.writerow([
            s.id,
            s.date,
            s.driver.name,
            s.vehicle.name,
            s.get_operating_model_display(),
            f'{s.total_income:.2f}',
            f'{s.total_expenses:.2f}',
            f'{s.gross_profit:.2f}',
            f'{s.driver_pay:.2f}',
            f'{s.total_owner_collected:.2f}',
            f'{s.debt_repaid:.2f}',
            f'{s.new_debt:.2f}',
            s.get_status_display(),
            s.approved_by.username if s.approved_by else '',
            s.approved_at.strftime('%Y-%m-%d %H:%M') if s.approved_at else '',
        ])

    return response


# ------------------------------------------------------------------
# Driver-facing views (mostly in driver_portal/views.py)
# These are stubs for shared or admin-override cases.
# ------------------------------------------------------------------
@login_required
def settlement_print(request, pk):
    """
    Print a settlement slip (shared view).
    Used by both owner and driver.
    """
    settlement = get_object_or_404(DailySettlement, pk=pk)

    # Check permission: driver can only print their own settlements
    if not request.user.is_staff and settlement.driver.portal_user != request.user:
        messages.error(request, 'You can only print your own settlements.')
        return redirect('driver:dashboard')

    context = {'settlement': settlement}
    return render(request, 'settlements/print.html', context)