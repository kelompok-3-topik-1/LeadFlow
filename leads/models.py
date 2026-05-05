from django.db import models

class Assignment(models.Model):

    id_assignment = models.CharField(db_column='ID_assignment', primary_key=True, max_length=10)  # Field name made lowercase.
    id_lead = models.ForeignKey('Leads', models.DO_NOTHING, db_column='ID_lead', blank=True, null=True)  # Field name made lowercase.
    id_user = models.ForeignKey('Users', models.DO_NOTHING, db_column='ID_user', blank=True, null=True)  # Field name made lowercase.
    assigned_at = models.DateTimeField(db_column='Assigned_at', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'assignment'


class Campaign(models.Model):
    id_campaign = models.CharField(db_column='ID_campaign', primary_key=True, max_length=10)  # Field name made lowercase.
    nama_camp = models.CharField(db_column='Nama_camp', max_length=100)  # Field name made lowercase.
    source = models.CharField(db_column='Source', max_length=100, blank=True, null=True)  # Field name made lowercase.
    production_cost = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    start_date = models.DateField(db_column='Start_date', blank=True, null=True)  # Field name made lowercase.
    end_date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'campaign'


class CampaignLeads(models.Model):
    id = models.CharField(db_column='Id', primary_key=True, max_length=10)  # Field name made lowercase.
    id_lead = models.ForeignKey('Leads', models.DO_NOTHING, db_column='Id_lead', blank=True, null=True)  # Field name made lowercase.
    id_camp = models.ForeignKey(Campaign, models.DO_NOTHING, db_column='Id_camp', blank=True, null=True)  # Field name made lowercase.
    funnel_position = models.CharField(db_column='Funnel_position', max_length=50, blank=True, null=True)  # Field name made lowercase.
    source = models.CharField(db_column='Source', max_length=100, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'campaign_leads'


class CustomFields(models.Model):
    id = models.CharField(db_column='Id', primary_key=True, max_length=10)  # Field name made lowercase.
    id_lead = models.ForeignKey('Leads', models.DO_NOTHING, db_column='Id_lead', blank=True, null=True)  # Field name made lowercase.
    field_name = models.CharField(db_column='Field_name', max_length=100, blank=True, null=True)  # Field name made lowercase.
    value = models.TextField(db_column='Value', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'custom_fields'


class Leads(models.Model):
    id_lead = models.CharField(db_column='ID_lead', primary_key=True, max_length=10)  # Field name made lowercase.
    nama = models.CharField(db_column='Nama', max_length=100)  # Field name made lowercase.
    email = models.CharField(db_column='Email', max_length=100, blank=True, null=True)  # Field name made lowercase.
    no_whatsapp = models.CharField(db_column='no_Whatsapp', max_length=20, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'leads'



class LeadsTag(models.Model):
    id = models.CharField(db_column='Id', primary_key=True, max_length=10)  # Field name made lowercase.
    id_tag = models.ForeignKey('Tag', models.DO_NOTHING, db_column='Id_tag', blank=True, null=True)  # Field name made lowercase.
    id_leads = models.ForeignKey(Leads, models.DO_NOTHING, db_column='Id_leads', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'leads_tag'


class LoginLogs(models.Model):
    id_log = models.CharField(db_column='ID_log', primary_key=True, max_length=10)
    id_user = models.ForeignKey('Users', models.DO_NOTHING, db_column='ID_user')
    login_time = models.DateTimeField(db_column='Login_time', blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.id_log:
            last_log = LoginLogs.objects.order_by('-id_log').first()
            if last_log:
                last_number = int(last_log.id_log.replace('LOG', ''))  # ← sesuaikan prefix
                new_number = last_number + 1
            else:
                new_number = 1
            self.id_log = f"LOG{new_number:03d}"  # ← sesuaikan prefix
        super().save(*args, **kwargs)

    class Meta:
        managed = False
        db_table = 'login_logs'


class RegistrationLinks(models.Model):
    id_link = models.CharField(db_column='Id_link', primary_key=True, max_length=10)  # Field name made lowercase.
    link_token = models.CharField(db_column='Link_token', unique=True, max_length=255)  # Field name made lowercase.
    id_camp = models.ForeignKey(Campaign, models.DO_NOTHING, db_column='Id_camp', blank=True, null=True)  # Field name made lowercase.
    generated_by = models.ForeignKey('Users', models.DO_NOTHING, db_column='Generated_by', blank=True, null=True)  # Field name made lowercase.
    generated_time = models.DateTimeField(db_column='Generated_time', blank=True, null=True)  # Field name made lowercase.
    expired_time = models.DateTimeField(db_column='Expired_time', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'registration_links'


class SegRule(models.Model):
    id_rule = models.CharField(db_column='Id_rule', primary_key=True, max_length=10)  # Field name made lowercase.
    id_seg = models.ForeignKey('Segmentasi', models.DO_NOTHING, db_column='Id_seg', blank=True, null=True)  # Field name made lowercase.
    field = models.CharField(db_column='Field', max_length=100, blank=True, null=True)  # Field name made lowercase.
    logic = models.CharField(db_column='Logic', max_length=20, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'seg_rule'


class Segmentasi(models.Model):
    id_seg = models.CharField(db_column='Id_seg', primary_key=True, max_length=10)  # Field name made lowercase.
    seg_name = models.CharField(db_column='Seg_name', max_length=100)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'segmentasi'


class Tag(models.Model):
    id_tag = models.CharField(db_column='Id_tag', primary_key=True, max_length=10)  # Field name made lowercase.
    label_tag = models.CharField(db_column='Label_tag', unique=True, max_length=100)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'tag'


class Users(models.Model):
    id_user = models.CharField(db_column='ID_user', primary_key=True, max_length=10)
    nama = models.CharField(db_column='Nama', max_length=100)
    email = models.CharField(db_column='Email', max_length=100, blank=True, null=True)
    role = models.CharField(db_column='Role', max_length=100, blank=True, null=True)
    asal_perusahaan = models.CharField(db_column='Asal_perusahaan', max_length=100)
    password = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.id_user:  # hanya generate kalau belum ada id
            last_user = Users.objects.order_by('-id_user').first()
            if last_user:
                last_number = int(last_user.id_user.replace('USR', ''))
                new_number = last_number + 1
            else:
                new_number = 1
            self.id_user = f"USR{new_number:03d}"  # hasil: USR001, USR002, dst
        super().save(*args, **kwargs)

    class Meta:
        managed = False
        db_table = 'users'