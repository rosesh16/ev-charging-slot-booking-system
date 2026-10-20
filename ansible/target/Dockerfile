FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       openssh-server python3 sudo ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash ansible \
    && usermod -aG sudo ansible \
    && printf 'ansible ALL=(ALL) NOPASSWD:ALL\n' > /etc/sudoers.d/ansible \
    && chmod 0440 /etc/sudoers.d/ansible \
    && mkdir -p /run/sshd /home/ansible/.ssh \
    && touch /home/ansible/.ssh/authorized_keys \
    && chown -R ansible:ansible /home/ansible/.ssh \
    && chmod 0700 /home/ansible/.ssh \
    && chmod 0600 /home/ansible/.ssh/authorized_keys

RUN printf '%s\n' \
    'PermitRootLogin no' \
    'PasswordAuthentication no' \
    'PubkeyAuthentication yes' \
    'AllowUsers ansible' \
    >> /etc/ssh/sshd_config

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D", "-e"]

COPY authorized_keys /home/ansible/.ssh/authorized_keys
RUN chown -R ansible:ansible /home/ansible/.ssh \
    && chmod 0700 /home/ansible/.ssh \
    && chmod 0600 /home/ansible/.ssh/authorized_keys
