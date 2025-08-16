terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Create VPC network
resource "google_compute_network" "vpc" {
  name                    = "livekit-vpc"
  auto_create_subnetworks = false
}

# Create subnet
resource "google_compute_subnetwork" "subnet" {
  name          = "livekit-subnet"
  ip_cidr_range = "10.0.0.0/24"
  network       = google_compute_network.vpc.id
  region        = var.region
}

# Create firewall rules
resource "google_compute_firewall" "allow_http" {
  name    = "allow-http"
  network = google_compute_network.vpc.id

  allow {
    protocol = "tcp"
    ports    = ["8000"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["livekit-voice-agent"]
}

resource "google_compute_firewall" "allow_livekit" {
  name    = "allow-livekit"
  network = google_compute_network.vpc.id

  allow {
    protocol = "tcp"
    ports    = ["7880", "7881"]
  }

  allow {
    protocol = "udp"
    ports    = ["7882"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["livekit-voice-agent"]
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "allow-ssh"
  network = google_compute_network.vpc.id

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["livekit-voice-agent"]
}

# Create VM instance
resource "google_compute_instance" "livekit_voice_agent" {
  name         = var.instance_name
  machine_type = var.machine_type
  zone         = var.zone

  tags = ["livekit-voice-agent"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = var.disk_size_gb
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.subnet.id
    access_config {
      // Ephemeral public IP
    }
  }

  metadata = {
    ssh-keys = "${var.ssh_user}:${file(var.ssh_public_key_path)}"
  }

  metadata_startup_script = file("${path.module}/../startup-script.sh")

  service_account {
    scopes = ["cloud-platform"]
  }

  depends_on = [
    google_compute_firewall.allow_http,
    google_compute_firewall.allow_livekit,
    google_compute_firewall.allow_ssh
  ]
}

# Output the external IP
output "external_ip" {
  value = google_compute_instance.livekit_voice_agent.network_interface[0].access_config[0].nat_ip
}

output "api_endpoint" {
  value = "http://${google_compute_instance.livekit_voice_agent.network_interface[0].access_config[0].nat_ip}:8000"
}
